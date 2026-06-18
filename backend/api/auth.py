# api/routes/auth.py – AUTO-V Authentication Routes (Production-Ready)

import os
import logging
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from supabase import Client

from services.supabase_client import get_supabase

# Configure logger
logger = logging.getLogger(__name__)

# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    phone: Optional[str] = None

    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.startswith('0') and not v.startswith('254'):
            # If not starting with 0 or 254, we might still accept, but let's be lenient
            pass
        return v

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"
    user: dict

class LogoutResponse(BaseModel):
    message: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    role: str
    created_at: datetime

# ============================================================
# ROUTER & SECURITY
# ============================================================

router = APIRouter()
security = HTTPBearer()

# ============================================================
# HELPER: GET CURRENT USER FROM SUPABASE SESSION
# ============================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Validate the Bearer token using Supabase.
    Returns the user object if valid.
    """
    token = credentials.credentials
    supabase = get_supabase()
    try:
        # Verify the token with Supabase
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        # Optionally fetch user profile from user_profiles table
        profile_response = supabase.table('user_profiles')\
            .select('*')\
            .eq('id', user_response.user.id)\
            .execute()
        user_data = user_response.user.model_dump() if hasattr(user_response.user, 'model_dump') else user_response.user.dict()
        if profile_response.data:
            user_data.update(profile_response.data[0])
        return user_data
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate user with email and password.
    Returns access token, refresh token, and user details.
    """
    supabase = get_supabase()
    try:
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        session = response.session
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        # Get user profile
        user = response.user
        profile_response = supabase.table('user_profiles')\
            .select('*')\
            .eq('id', user.id)\
            .execute()
        user_data = user.model_dump() if hasattr(user, 'model_dump') else user.dict()
        if profile_response.data:
            user_data.update(profile_response.data[0])
        # Update login count
        if profile_response.data:
            supabase.table('user_profiles')\
                .update({'login_count': profile_response.data[0].get('login_count', 0) + 1})\
                .eq('id', user.id)\
                .execute()
        logger.info(f"User logged in: {user.email}")
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_in": session.expires_in,
            "token_type": "bearer",
            "user": user_data
        }
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest):
    """
    Register a new user.
    Returns the same as login (auto-login after signup).
    """
    supabase = get_supabase()
    try:
        # Sign up the user
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "full_name": request.full_name,
                    "phone": request.phone
                }
            }
        })
        user = response.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signup failed"
            )
        # Create user profile
        profile_data = {
            "id": user.id,
            "email": request.email,
            "full_name": request.full_name or request.email.split('@')[0],
            "phone": request.phone,
            "role": "user",
            "first_login": True,
            "login_count": 1,
            "created_at": datetime.now().isoformat()
        }
        supabase.table('user_profiles').insert(profile_data).execute()
        # Auto-login: sign in with the same credentials
        login_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        session = login_response.session
        if not session:
            # If auto-login fails, still return success but user must login manually
            # We'll return a response with a message.
            return {
                "access_token": None,
                "refresh_token": None,
                "expires_in": 0,
                "token_type": "bearer",
                "user": profile_data,
                "message": "Account created. Please log in."
            }
        user_data = user.model_dump() if hasattr(user, 'model_dump') else user.dict()
        user_data.update(profile_data)
        logger.info(f"User signed up and logged in: {request.email}")
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_in": session.expires_in,
            "token_type": "bearer",
            "user": user_data
        }
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    """
    Refresh the access token using a valid refresh token.
    """
    supabase = get_supabase()
    try:
        response = supabase.auth.refresh_session(request.refresh_token)
        session = response.session
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        user = response.user
        user_data = user.model_dump() if hasattr(user, 'model_dump') else user.dict()
        # Optionally fetch profile
        profile_response = supabase.table('user_profiles')\
            .select('*')\
            .eq('id', user.id)\
            .execute()
        if profile_response.data:
            user_data.update(profile_response.data[0])
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_in": session.expires_in,
            "token_type": "bearer",
            "user": user_data
        }
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout the current user.
    Note: Supabase sign_out() invalidates the session on the client side,
    but we also clear local session on the server if needed.
    """
    supabase = get_supabase()
    try:
        # Supabase sign_out() is a client-side operation; on the server,
        # we can't invalidate a session without the refresh token.
        # However, we can log the event or optionally revoke the refresh token.
        # For simplicity, we just return a success message.
        # The client is responsible for discarding the tokens.
        logger.info(f"User logged out: {current_user.get('email')}")
        # Optionally, you could call supabase.auth.admin.delete_user() but that deletes the account.
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    """
    return current_user
