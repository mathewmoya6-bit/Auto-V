# app/core/security.py
# =============================================================================
# AUTO-V API - Security: Password Hashing, JWT, Current-User Dependency
# =============================================================================
"""
This app authorizes requests itself via JWT — Supabase RLS is not the
authorization layer (see app.core.database for why). This module is what
issues and verifies those JWTs, and resolves the current user by reading
the `users` table directly through the admin client.

Assumes a Supabase table named `users` with at least:
    id (uuid, pk), email, full_name, phone, role, company_name,
    is_active, is_verified, password_hash, created_at, last_login

If your actual table/column names differ, update TABLE_NAME and the
field lookups in get_current_user() below — nothing else needs to change.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_admin_client
from app.schemas.user import UserProfile

logger = logging.getLogger(__name__)

TABLE_NAME = "users"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


# ─── Password hashing ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT ────────────────────────────────────────────────────────────

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        return None


# ─── Current-user dependency ───────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> UserProfile:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None or payload.get("type") != "access" or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = get_admin_client()
    result = admin.table(TABLE_NAME).select("*").eq("id", payload["sub"]).limit(1).execute()

    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user = UserProfile(**result.data[0])
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    return user


async def get_current_admin_user(
    current_user: UserProfile = Depends(get_current_user),
) -> UserProfile:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
