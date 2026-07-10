# app/api/v1/endpoints/auth.py
# =============================================================================
# AUTO-V API - Auth Endpoints
# =============================================================================
"""
All auth goes through Supabase Auth directly (email + password). Supabase
handles password hashing, verification, and session/token issuance — we
just relay its response back to the frontend in the shape auto-v-api.js
expects:

    POST /auth/login    -> { access_token, refresh_token, ... }
    POST /auth/refresh  -> { access_token, refresh_token, ... }
    GET  /auth/me        -> current user (requires Bearer token)
    POST /auth/logout   -> { success: true }
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.deps import get_current_user
from app.core.supabase_client import supabase_anon

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str


# ─── Login ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
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

    return AuthResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        user_id=user.id,
        email=user.email,
    )


# ─── Refresh ──────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=AuthResponse)
async def refresh(payload: RefreshRequest):
    try:
        result = supabase_anon.auth.refresh_session(payload.refresh_token)
    except Exception as exc:
        logger.warning(f"Token refresh failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    session = result.session
    user = result.user

    if not session or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    return AuthResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        user_id=user.id,
        email=user.email,
    )


# ─── Current user ───────────────────────────────────────────────────────

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": (user.user_metadata or {}).get("full_name"),
        "role": (user.app_metadata or {}).get("role")
        or (user.user_metadata or {}).get("role")
        or "user",
        "phone": (user.user_metadata or {}).get("phone"),
        "company": (user.user_metadata or {}).get("company"),
        "email_confirmed_at": user.email_confirmed_at,
    }


# ─── Logout ───────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    # Supabase access tokens are short-lived JWTs; there is no per-token
    # server-side revocation call needed here for the anon-key flow — the
    # frontend clears its stored tokens on this response. If you need hard
    # server-side session revocation, use supabase_admin.auth.admin
    # .sign_out(user.id) with the service role client instead.
    return {"success": True}
