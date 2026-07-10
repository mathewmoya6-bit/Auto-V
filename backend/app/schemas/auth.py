# app/schemas/auth.py
"""
MERGE this into your existing app/schemas/auth.py — don't overwrite it.
Your real file already has TokenResponse, UserLogin, UserRegister (per your
API's schema list); only `RefreshRequest` and `RefreshResponse` are new
additions from this round of fixes. Everything else below is my best
reconstruction of what's likely already there, included only so this file
is runnable standalone if you want to diff against it.
"""
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    # TODO(integration): add this field once login starts issuing refresh
    # tokens too — required for the /auth/refresh endpoint to have anything
    # to exchange.
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


# --- NEW: needed for POST /api/v1/auth/refresh ------------------------------

class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
