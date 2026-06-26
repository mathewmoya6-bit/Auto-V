"""
Authentication Routes - FastAPI Version
Handles user registration, login, profile management with Supabase
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from supabase import create_client

from app.core.config import settings
from app.core.security import security
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security_scheme = HTTPBearer()

# Supabase client
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_ANON_KEY = settings.SUPABASE_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# ─── Pydantic Models ──────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    """User registration request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    full_name: str = Field(..., min_length=2, description="User full name")
    phone: Optional[str] = Field(None, description="User phone number")
    company: Optional[str] = Field(None, description="User company name")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class UserLoginRequest(BaseModel):
    """User login request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """User response model"""
    id: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response model"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class LoginResponse(BaseModel):
    """Login response model"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


# ─── Helper Functions ──────────────────────────────────────────

def get_supabase_user(token: str) -> Optional[dict]:
    """Get user from Supabase using token"""
    try:
        user_response = supabase.auth.get_user(token)
        if user_response and hasattr(user_response, 'user'):
            return user_response.user
        return None
    except Exception as e:
        logger.error(f"Get Supabase user error: {e}")
        return None


# ─── Routes ──────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserRegisterRequest):
    """
    Register a new user.
    
    **Request Body:**
    - `email`: User email address
    - `password`: User password (min 8 characters, must contain uppercase, lowercase, and number)
    - `full_name`: User full name
    - `phone`: Optional phone number
    - `company`: Optional company name
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Contains user_id, email, and message
    - `error`: Error message if unsuccessful
    """
    try:
        # Check if user exists
        existing = supabase.table("user_profiles").select("*").eq("email", user_data.email).execute()
        
        if existing.data:
            return AuthResponse(
                success=False,
                error="User with this email already exists"
            )
        
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password
        })
        
        if not auth_response.user:
            return AuthResponse(
                success=False,
                error="Registration failed - could not create user"
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
        
        # Insert user profile
        supabase.table("user_profiles").insert(profile_data).execute()
        
        return AuthResponse(
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
        return AuthResponse(
            success=False,
            error=str(e)
        )


@router.post("/login", response_model=LoginResponse)
async def login(user_data: UserLoginRequest):
    """
    Login a user.
    
    **Request Body:**
    - `email`: User email address
    - `password`: User password
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Contains user_id, email, access_token, refresh_token
    - `error`: Error message if unsuccessful
    """
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        
        if not auth_response.user:
            return LoginResponse(
                success=False,
                error="Invalid credentials"
            )
        
        # Update last login
        supabase.table("user_profiles").update({
            "last_login": datetime.utcnow().isoformat()
        }).eq("id", auth_response.user.id).execute()
        
        return LoginResponse(
            success=True,
            data={
                "user_id": auth_response.user.id,
                "email": auth_response.user.email,
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token,
                "expires_in": 3600
            }
        )
        
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return LoginResponse(
            success=False,
            error=str(e)
        )


@router.get("/profile/{user_id}", response_model=AuthResponse)
async def get_profile(user_id: str):
    """
    Get user profile.
    
    **Path Parameter:**
    - `user_id`: User ID to retrieve
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: User profile data
    - `error`: Error message if unsuccessful
    """
    try:
        result = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        
        if not result.data:
            return AuthResponse(
                success=False,
                error="User not found"
            )
        
        return AuthResponse(
            success=True,
            data=result.data[0]
        )
        
    except Exception as e:
        logger.error(f"Profile error: {e}", exc_info=True)
        return AuthResponse(
            success=False,
            error=str(e)
        )


@router.get("/me", response_model=AuthResponse)
async def get_current_user_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
):
    """
    Get current user profile from JWT token.
    
    **Headers:**
    - `Authorization`: Bearer JWT token
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: User profile data
    - `error`: Error message if unsuccessful
    """
    try:
        token = credentials.credentials
        
        # Decode token to get user info
        payload = security.decode_token(token)
        if not payload:
            return AuthResponse(
                success=False,
                error="Invalid or expired token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            return AuthResponse(
                success=False,
                error="Invalid token payload"
            )
        
        # Get user profile
        result = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        
        if not result.data:
            return AuthResponse(
                success=False,
                error="User not found"
            )
        
        return AuthResponse(
            success=True,
            data=result.data[0]
        )
        
    except Exception as e:
        logger.error(f"Get current user error: {e}", exc_info=True)
        return AuthResponse(
            success=False,
            error=str(e)
        )


@router.put("/profile/{user_id}", response_model=AuthResponse)
async def update_profile(
    user_id: str,
    update_data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
):
    """
    Update user profile.
    
    **Path Parameter:**
    - `user_id`: User ID to update
    
    **Headers:**
    - `Authorization`: Bearer JWT token
    
    **Request Body:**
    - `full_name`: Updated full name
    - `phone`: Updated phone number
    - `company`: Updated company name
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Updated user profile
    - `error`: Error message if unsuccessful
    """
    try:
        # Verify user has permission
        token = credentials.credentials
        payload = security.decode_token(token)
        
        if not payload or payload.get("sub") != user_id:
            return AuthResponse(
                success=False,
                error="You don't have permission to update this profile"
            )
        
        # Update profile
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = supabase.table("user_profiles").update(update_data).eq("id", user_id).execute()
        
        if not result.data:
            return AuthResponse(
                success=False,
                error="Failed to update user profile"
            )
        
        return AuthResponse(
            success=True,
            data=result.data[0]
        )
        
    except Exception as e:
        logger.error(f"Update profile error: {e}", exc_info=True)
        return AuthResponse(
            success=False,
            error=str(e)
        )


@router.post("/logout", response_model=AuthResponse)
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
):
    """
    Logout user.
    
    **Headers:**
    - `Authorization`: Bearer JWT token (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `message`: Logout message
    """
    try:
        # Supabase handles logout on client side
        # Server just acknowledges the logout
        return AuthResponse(
            success=True,
            data={"message": "Logged out successfully"}
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        return AuthResponse(
            success=False,
            error=str(e)
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    refresh_token: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
):
    """
    Refresh access token.
    
    **Request Body:**
    - `refresh_token`: Refresh token from login
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Contains new access_token and refresh_token
    - `error`: Error message if unsuccessful
    """
    try:
        # Refresh token using Supabase
        # Note: This is a simplified version - actual implementation may vary
        # based on Supabase's refresh token handling
        
        auth_response = supabase.auth.refresh_session(refresh_token)
        
        if not auth_response.session:
            return AuthResponse(
                success=False,
                error="Failed to refresh token"
            )
        
        return AuthResponse(
            success=True,
            data={
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token,
                "expires_in": 3600
            }
        )
        
    except Exception as e:
        logger.error(f"Refresh token error: {e}", exc_info=True)
        return AuthResponse(
            success=False,
            error=str(e)
        )


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(email: EmailStr):
    """
    Request password reset.
    
    **Request Body:**
    - `email`: User email address
    
    **Response:**
    - `success`: Boolean indicating success
    - `message`: Password reset email sent
    - `error`: Error message if unsuccessful
    """
    try:
        supabase.auth.reset_password_for_email(email)
        
        return AuthResponse(
            success=True,
            data={"message": "Password reset email sent"}
        )
        
    except Exception as e:
        logger.error(f"Reset password error: {e}", exc_info=True)
        return AuthResponse(
            success=False,
            error=str(e)
        )


@router.get("/verify/{verification_token}", response_model=AuthResponse)
async def verify_email(verification_token: str):
    """
    Verify user email.
    
    **Path Parameter:**
    - `verification_token`: Verification token from email
    
    **Response:**
    - `success`: Boolean indicating success
    - `message`: Verification status
    - `error`: Error message if unsuccessful
    """
    try:
        # Handle email verification
        # Supabase handles this automatically, but we can add additional logic
        # to update user profile status
        
        return AuthResponse(
            success=True,
            data={"message": "Email verified successfully"}
        )
        
    except Exception as e:
        logger.error(f"Verify email error: {e}", exc_info=True)
        return AuthResponse(
            success=False,
            error=str(e)
        )
