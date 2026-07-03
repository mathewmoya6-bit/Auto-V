# app/api/v1/routes/auth.py
# =============================================================================
# AUTO-V API - Authentication Routes
# =============================================================================
#
# NOTE ON SCOPE: actual login/signup/password-reset already happens
# client-side against Supabase Auth (supabase.js: signInWithPassword,
# signOut, etc.) — this backend never sees a raw password. So this
# router doesn't re-implement login; it just exposes what a backend
# typically needs once the frontend already holds a Supabase session
# token: confirming that token is valid, and returning/creating the
# matching profile.
#
# The /login endpoint below is provided as a CONVENIENCE for frontends
# that want to use this backend as a proxy. It forwards credentials to
# Supabase and returns the session token. This keeps the frontend
# simpler and centralizes Supabase configuration.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
import logging

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import UserProfile
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class LoginRequest(BaseModel):
    """Login request model."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@autov.co.ke",
                "password": "your_password"
            }
        }


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: Optional[int] = Field(default=3600, description="Token expiry in seconds")
    user: dict = Field(..., description="User profile information")


# =============================================================================
# LOGIN ENDPOINT - PROXY TO SUPABASE
# =============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate a user via Supabase Auth.
    
    This endpoint acts as a proxy to Supabase Auth, allowing frontends
    to use a single backend endpoint instead of configuring Supabase
    credentials on the client side.
    
    Args:
        credentials: Email and password
        db: Database session
        
    Returns:
        LoginResponse with access token and user profile
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Import Supabase client
        from supabase import create_client
        
        # Initialize Supabase client
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        if not auth_response or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Get user profile from database
        from app.models import UserProfile
        user = await db.execute(
            UserProfile.select().where(
                UserProfile.email == credentials.email
            )
        )
        user_profile = user.scalar_one_or_none()
        
        if not user_profile:
            # User exists in Supabase but not in our database
            # Create a basic profile
            user_profile = UserProfile(
                email=credentials.email,
                role="user",
                is_active=True
            )
            db.add(user_profile)
            await db.commit()
            await db.refresh(user_profile)
        
        # Return response with token
        return LoginResponse(
            access_token=auth_response.session.access_token,
            token_type="bearer",
            expires_in=auth_response.session.expires_in,
            user={
                "id": str(user_profile.id),
                "email": user_profile.email,
                "role": user_profile.role,
                "full_name": getattr(user_profile, "full_name", None),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )


# =============================================================================
# ME ENDPOINT
# =============================================================================

@router.get("/me")
async def get_me(current_user: UserProfile = Depends(get_current_user)):
    """Return the profile for whoever's Supabase access_token was sent
    in the Authorization header. Confirms the token is valid and gives
    the frontend a single place to fetch role/profile info from this
    backend rather than querying Supabase directly, if desired."""
    return current_user.to_dict()


# =============================================================================
# VERIFY ENDPOINT
# =============================================================================

@router.post("/verify")
async def verify_token(current_user: UserProfile = Depends(get_current_user)):
    """Lightweight endpoint the frontend can call just to check whether
    a stored session token is still valid (e.g. on app load)."""
    return {
        "valid": True,
        "user_id": str(current_user.id),
        "role": current_user.role,
        "email": current_user.email
    }


# =============================================================================
# LOGOUT ENDPOINT
# =============================================================================

@router.post("/logout")
async def logout():
    """
    Logout endpoint - invalidates the current session.
    NOTE: Since Supabase handles session management, this endpoint
    simply returns a success response. The frontend should clear
    the local session token.
    """
    return {
        "message": "Logged out successfully",
        "status": "success"
    }


# =============================================================================
# REFRESH TOKEN ENDPOINT
# =============================================================================

class RefreshRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str = Field(..., description="Refresh token")


@router.post("/refresh")
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh the access token using a refresh token.
    
    Args:
        request: Refresh token
        db: Database session
        
    Returns:
        New access token
    """
    try:
        from supabase import create_client
        
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Refresh session with Supabase
        auth_response = supabase.auth.refresh_session(request.refresh_token)
        
        if not auth_response or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "expires_in": auth_response.session.expires_in,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


# =============================================================================
# PASSWORD RESET ENDPOINTS
# =============================================================================

class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    email: str = Field(..., description="User email address")


@router.post("/password-reset")
async def request_password_reset(
    request: PasswordResetRequest
):
    """
    Request a password reset email.
    
    Args:
        request: Email address
        
    Returns:
        Success message
    """
    try:
        from supabase import create_client
        
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Send password reset email via Supabase
        supabase.auth.reset_password_for_email(request.email)
        
        return {
            "message": "Password reset email sent",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )


class PasswordUpdateRequest(BaseModel):
    """Password update request model."""
    new_password: str = Field(..., description="New password", min_length=6)


@router.post("/password-update")
async def update_password(
    request: PasswordUpdateRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update the current user's password.
    
    Args:
        request: New password
        current_user: Current user profile
        
    Returns:
        Success message
    """
    try:
        from supabase import create_client
        
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Update user password via Supabase
        supabase.auth.update_user({
            "password": request.new_password
        })
        
        return {
            "message": "Password updated successfully",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Password update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
