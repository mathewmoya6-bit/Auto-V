"""
Authentication Routes - FastAPI Version
Handles user registration, login, profile management with JWT
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr

from app.core.database import supabase
from app.core.auth_middleware import (
    generate_token_pair,
    verify_refresh_token,
    get_current_user,
    get_current_user_optional
)
from app.schemas.user import UserRegisterRequest, UserLoginRequest, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ─── Routes ──────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegisterRequest):
    """Register a new user."""
    try:
        # Check if user exists
        existing = supabase.table("user_profiles").select("*").eq("email", user_data.email).execute()
        
        if existing.data:
            return UserResponse(
                success=False,
                error="User with this email already exists"
            )
        
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password
        })
        
        if not auth_response.user:
            return UserResponse(
                success=False,
                error="Registration failed"
            )
        
        # Create user profile
        profile_data = {
            "id": auth_response.user.id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "phone": user_data.phone,
            "company": user_data.company,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("user_profiles").insert(profile_data).execute()
        
        return UserResponse(
            success=True,
            data={
                "user_id": auth_response.user.id,
                "email": user_data.email,
                "full_name": user_data.full_name,
                "message": "User registered successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return UserResponse(
            success=False,
            error=str(e)
        )


@router.post("/login")
async def login(user_data: UserLoginRequest):
    """Login user and return JWT tokens."""
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Update last login
        supabase.table("user_profiles").update({
            "last_login": datetime.utcnow().isoformat()
        }).eq("id", auth_response.user.id).execute()
        
        # Get user profile
        profile_result = supabase.table("user_profiles").select("*").eq("id", auth_response.user.id).execute()
        profile = profile_result.data[0] if profile_result.data else {}
        
        # Generate JWT tokens
        tokens = generate_token_pair(
            user_id=auth_response.user.id,
            email=auth_response.user.email,
            role=profile.get("role", "user")
        )
        
        return {
            "success": True,
            "data": {
                "user": {
                    "id": auth_response.user.id,
                    "email": auth_response.user.email,
                    "full_name": profile.get("full_name"),
                    "phone": profile.get("phone"),
                    "company": profile.get("company"),
                    "role": profile.get("role", "user")
                },
                **tokens
            }
        }
        
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token."""
    try:
        # Verify refresh token
        payload = verify_refresh_token(refresh_token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role", "user")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Generate new tokens
        tokens = generate_token_pair(user_id, email, role)
        
        return {
            "success": True,
            "data": tokens
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh token error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user_optional)):
    """Logout user."""
    # Supabase handles logout on client side
    # Server just acknowledges the logout
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.get("/me")
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    try:
        user_id = current_user.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user profile
        result = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "success": True,
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
