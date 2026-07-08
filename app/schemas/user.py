# app/schemas/user.py
# =============================================================================
# AUTO-V API - User Schemas
# =============================================================================
"""
UserProfile is the single canonical shape for a user record returned by
the API. Other modules (e.g. schemas.auth) should alias this rather than
redefining an equivalent class — duplicate near-identical schemas drifting
out of sync is what caused most of this app's earlier import failures.
"""
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator


class UserProfile(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "user"
    company_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2)
    phone: Optional[str] = None
    company_name: Optional[str] = None
    is_active: Optional[bool] = None

    @validator("phone")
    def validate_phone(cls, v):
        if v and not re.match(r"^\+?[0-9]{10,15}$", v):
            raise ValueError("Phone number must be 10-15 digits with optional + prefix")
        return v
