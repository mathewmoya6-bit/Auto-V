# app/api/v1/endpoints/auth.py
# =============================================================================
# AUTO-V API - Auth Endpoints
# =============================================================================
"""
Login goes through Supabase Auth directly (email + password). Supabase
handles password hashing, verification, and session/token issuance —
we just relay its response back to the frontend in a clean shape.
"""
import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.supabase_client import supabase_anon

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    try:
        result = supabase_anon.auth.sign_in_with_password(
            {
                "email": credentials.email,
                "password": credentials.password,
            }
        )
    except Exception as exc:
        # supabase-py raises AuthApiError (and friends) on bad credentials,
        # unconfirmed email, etc. Treat all of these as 401 rather than
        # leaking internal error details to the client.
        logger.warning(f"Login failed for {credentials.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    session = result.session
    user = result.user

    if not session or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return LoginResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        user_id=user.id,
        email=user.email,
    )
