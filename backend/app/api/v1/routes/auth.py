# app/api/v1/routes/auth.py
# =============================================================================
# AUTO-V API - Authentication Routes (Supabase)
# =============================================================================

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.supabase import (
    sign_up_user, sign_in_user, sign_out_user, 
    get_user_by_token, refresh_access_token, reset_password,
    is_supabase_configured
)
from app.models.user import UserProfile

logger = logging.getLogger(__name__)

# ─── Router ──────────────────────────────────────────────────────────
router = APIRouter(tags=["Authentication"])


# ─── Pydantic Models ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters")
    full_name: str = Field(..., description="User's full name")
    phone: Optional[str] = Field(None, description="Phone number")
    company_name: Optional[str] = Field(None, description="Company name")


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Authentication token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: int
    user: dict


class UserResponse(BaseModel):
    """User information response"""
    id: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_verified: bool
    created_at: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr


# ─── Dependencies ──────────────────────────────────────────────────

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    Get current authenticated user from Supabase token
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = parts[1]
    
    user = await get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return user


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get current active user"""
    return current_user


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get current admin user"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


# ─── Routes ──────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user using Supabase Auth
    """
    if not is_supabase_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    # Register with Supabase
    result = await sign_up_user(
        email=payload.email,
        password=payload.password,
        user_metadata={
            "full_name": payload.full_name,
            "phone": payload.phone,
            "company_name": payload.company_name,
            "role": "user"
        }
    )
    
    if not result["success"]:
        error_msg = result.get("error", "Registration failed")
        if "already registered" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Also save user to your local database for additional data
    try:
        # Check if user exists in local DB
        existing = await db.execute(
            select(UserProfile).where(UserProfile.email == payload.email.lower())
        )
        if not existing.scalar_one_or_none():
            # Create local user record
            user = UserProfile(
                id=result["user"]["id"],
                email=payload.email.lower(),
                full_name=payload.full_name,
                phone=payload.phone,
                company_name=payload.company_name,
                role="user",
                is_active=True,
                is_verified=result["user"]["is_verified"]
            )
            db.add(user)
            await db.commit()
    except Exception as e:
        logger.warning(f"Could not create local user record: {e}")
        # Continue - user is already in Supabase
    
    return {
        "message": "User registered successfully. Please verify your email.",
        "user": result["user"]
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login user using Supabase Auth
    """
    if not is_supabase_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    # Login with Supabase
    result = await sign_in_user(
        email=payload.email,
        password=payload.password
    )
    
    if not result["success"]:
        error_msg = result.get("error", "Login failed")
        if "invalid" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        elif "verify" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before logging in"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg
        )
    
    # Update local user record
    try:
        user_result = await db.execute(
            select(UserProfile).where(UserProfile.email == payload.email.lower())
        )
        user = user_result.scalar_one_or_none()
        if user:
            user.last_login = None  # Will be updated
            await db.commit()
    except Exception as e:
        logger.warning(f"Could not update local user: {e}")
    
    return TokenResponse(
        access_token=result["session"]["access_token"],
        refresh_token=result["session"]["refresh_token"],
        expires_at=result["session"]["expires_at"],
        user=result["user"]
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user profile
    """
    return current_user


@router.post("/refresh")
async def refresh_token(
    refresh_token: str
):
    """
    Refresh access token
    """
    if not is_supabase_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    result = await refresh_access_token(refresh_token)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.get("error", "Token refresh failed")
        )
    
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "expires_at": result["expires_at"]
    }


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user)
):
    """
    Logout user
    """
    await sign_out_user(current_user["id"])
    return {"message": "Logged out successfully"}


@router.post("/reset-password")
async def request_password_reset(
    payload: PasswordResetRequest
):
    """
    Request password reset email
    """
    if not is_supabase_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    result = await reset_password(payload.email)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Password reset failed")
        )
    
    return {"message": "Password reset email sent"}


@router.get("/ping")
async def ping():
    """
    Ping endpoint to test if auth router is working
    """
    return {
        "status": "ok",
        "message": "Authentication router is working (Supabase)",
        "supabase_configured": is_supabase_configured()
    }
