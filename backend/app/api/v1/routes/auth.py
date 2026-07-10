# app/api/v1/routes/auth.py
# =============================================================================
# AUTO-V API - Auth Routes
# =============================================================================
from fastapi import APIRouter, Depends, status, HTTPException

from app.core.security import get_current_user
from app.schemas.auth import (
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(tags=["Authentication"])


def get_auth_service() -> AuthService:
    return AuthService()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, service: AuthService = Depends(get_auth_service)):
    """Register a new user"""
    return await service.signup(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, service: AuthService = Depends(get_auth_service)):
    """Login user with email and password"""
    return await service.login(payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    """Refresh access token using refresh token"""
    return await service.refresh(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current authenticated user's profile"""
    return current_user


@router.post("/logout")
async def logout(current_user: UserResponse = Depends(get_current_user)):
    """Logout current user"""
    # In Supabase, logout is handled client-side
    # This endpoint exists for API completeness
    return {"message": "Logged out successfully"}
