# backend/app/schemas/auth.py
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserLogin(BaseModel):
    """Request model for user login"""
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    """Request model for user registration"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None


class TokenResponse(BaseModel):
    """Response model for authentication tokens"""
    access_token: str
    refresh_token: str
    user: dict


class RefreshRequest(BaseModel):
    """Request model for refreshing tokens"""
    refresh_token: str


class RefreshResponse(BaseModel):
    """Response model for token refresh"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response model for user information"""
    id: str
    email: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False


# Export all classes
__all__ = [
    "UserLogin",
    "UserRegister",
    "TokenResponse",
    "RefreshRequest",
    "RefreshResponse",
    "UserResponse"
]
