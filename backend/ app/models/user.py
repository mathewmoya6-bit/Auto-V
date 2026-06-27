# app/models/user.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone_number: str = Field(..., min_length=10, max_length=15)
    
    @validator('phone_number')
    def validate_phone(cls, v):
        # Remove any spaces
        v = v.replace(' ', '')
        
        # Check if phone number is valid Kenyan format
        if not v.startswith('254') and not v.startswith('0'):
            raise ValueError('Phone number must start with 254 or 0')
        
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=50)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "user"
    email_verified: bool = False
    phone_number: Optional[str] = None
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserProfile(BaseModel):
    user_id: str
    profile_picture: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    preferences: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

class UserSettings(BaseModel):
    email_notifications: bool = True
    sms_notifications: bool = True
    two_factor_auth: bool = False
    language: str = "en"
    currency: str = "KES"
    
    class Config:
        from_attributes = True
