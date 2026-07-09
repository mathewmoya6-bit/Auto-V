# app/schemas/auth.py
# =============================================================================
# AUTO-V API - Auth Schemas
# =============================================================================
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator

from app.schemas.user import UserProfile


class UserCreate(BaseModel):
    """Registration payload."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    company_name: Optional[str] = None

    @validator("password")
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

    @validator("phone")
    def validate_phone(cls, v):
        if v and not re.match(r"^\+?[0-9]{10,15}$", v):
            raise ValueError("Phone number must be 10-15 digits with optional + prefix")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


UserResponse = UserProfile

TokenResponse.model_rebuild()
