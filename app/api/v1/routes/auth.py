# app/api/v1/routes/auth.py
# =============================================================================
# AUTO-V API - Auth Routes
# =============================================================================
from fastapi import APIRouter, Depends, status

from app.core.security import get_current_user
from app.schemas.auth import (
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service() -> AuthService:
    return AuthService()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, service: AuthService = Depends(get_auth_service)):
    return await service.signup(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, service: AuthService = Depends(get_auth_service)):
    return await service.login(payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    return await service.refresh(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user
