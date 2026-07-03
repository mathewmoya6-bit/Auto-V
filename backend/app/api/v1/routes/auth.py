# app/api/v1/routes/auth.py
# =============================================================================
# AUTO-V API - Authentication Routes
# =============================================================================

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import UserProfile
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─── Request Models ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: dict = Field(..., description="User profile information")


# ─── Login Endpoint ──────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate a user via Supabase Auth.
    
    Args:
        credentials: Email and password
        db: Database session
        
    Returns:
        LoginResponse with access token and user profile
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        logger.info(f"🔐 Login attempt for: {credentials.email}")
        
        # Import Supabase client
        from supabase import create_client
        
        # Initialize Supabase client
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.error("❌ Supabase credentials not configured!")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service not configured"
            )
        
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Authenticate with Supabase
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": credentials.email,
                "password": credentials.password
            })
            
            if not auth_response or not auth_response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            logger.info(f"✅ Supabase auth successful for: {credentials.email}")
            
        except Exception as auth_error:
            logger.error(f"❌ Supabase auth error: {str(auth_error)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Get or create user profile in database
        from app.models import UserProfile
        from sqlalchemy import select
        
        # Check if user exists in our database
        result = await db.execute(
            select(UserProfile).where(UserProfile.email == credentials.email)
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            # Create basic profile
            user_profile = UserProfile(
                email=credentials.email,
                role="user",
                is_active=True
            )
            db.add(user_profile)
            await db.commit()
            await db.refresh(user_profile)
            logger.info(f"✅ Created user profile for: {credentials.email}")
        
        # Return response with token
        return LoginResponse(
            access_token=auth_response.session.access_token,
            token_type="bearer",
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
        logger.error(f"❌ Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )


# ─── Get Current User ──────────────────────────────────────────────

@router.get("/me")
async def get_me(current_user: UserProfile = Depends(get_current_user)):
    """Return the current user profile."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "full_name": getattr(current_user, "full_name", None),
    }


@router.post("/verify")
async def verify_token(current_user: UserProfile = Depends(get_current_user)):
    """Verify if the current token is valid."""
    return {
        "valid": True,
        "user_id": str(current_user.id),
        "role": current_user.role,
        "email": current_user.email,
    }


@router.post("/logout")
async def logout():
    """Logout endpoint."""
    return {"message": "Logged out successfully", "status": "success"}
