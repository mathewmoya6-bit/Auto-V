# app/api/v1/routes/auth.py
# =============================================================================
# AUTO-V API - Authentication Routes
# =============================================================================

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional

from app.core.database import get_db
from app.models.user import UserProfile
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: dict = Field(..., description="User profile information")


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate a user via Supabase Auth."""
    try:
        logger.info(f"🔐 Login attempt for: {credentials.email}")
        
        from supabase import create_client
        
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
        
        # Get or create user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.email == credentials.email)
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            user_profile = UserProfile(
                email=credentials.email,
                role="user",
                is_active=True
            )
            db.add(user_profile)
            await db.commit()
            await db.refresh(user_profile)
            logger.info(f"✅ Created user profile for: {credentials.email}")
        
        return LoginResponse(
            access_token=auth_response.session.access_token,
            token_type="bearer",
            user={
                "id": str(user_profile.id),
                "email": user_profile.email,
                "role": user_profile.role,
                "full_name": user_profile.full_name,
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


@router.get("/me")
async def get_me(
    db: AsyncSession = Depends(get_db),
    # current_user: UserProfile = Depends(get_current_user)
):
    """Get current user profile."""
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "role": "user",
        "full_name": "Test User",
    }
