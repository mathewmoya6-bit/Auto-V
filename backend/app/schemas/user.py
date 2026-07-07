# app/schemas/user.py
# =============================================================================
# AUTO-V API - User Schemas
# =============================================================================

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re


class UserProfile(BaseModel):
    """User profile schema."""
    
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
    """Schema for updating user profile."""
    
    full_name: Optional[str] = Field(None, min_length=2)
    phone: Optional[str] = None
    company_name: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+?[0-9]{10,15}$', v):
            raise ValueError('Phone number must be 10-15 digits with optional + prefix')
        return v
