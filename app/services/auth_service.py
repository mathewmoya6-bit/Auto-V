# app/services/auth_service.py
# =============================================================================
# AUTO-V API - Auth Service
# =============================================================================
"""
All auth business logic lives here. Routes call this; this is the only
thing that touches the `users` table for auth purposes.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.core.database import get_admin_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserResponse

logger = logging.getLogger(__name__)

TABLE_NAME = "users"


class AuthService:
    def __init__(self):
        self.db = get_admin_client()

    async def signup(self, payload: UserCreate) -> TokenResponse:
        existing = (
            self.db.table(TABLE_NAME)
            .select("id")
            .eq("email", payload.email)
            .limit(1)
            .execute()
        )
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        record = {
            "email": payload.email,
            "password_hash": hash_password(payload.password),
            "full_name": payload.full_name,
            "phone": payload.phone,
            "company_name": payload.company_name,
            "role": "user",
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = self.db.table(TABLE_NAME).insert(record).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )

        user_row = result.data[0]
        return self._issue_tokens(user_row)

    async def login(self, payload: UserLogin) -> TokenResponse:
        result = (
            self.db.table(TABLE_NAME)
            .select("*")
            .eq("email", payload.email)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
            )

        user_row = result.data[0]

        if not verify_password(payload.password, user_row.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
            )

        if not user_row.get("is_active", True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

        self.db.table(TABLE_NAME).update(
            {"last_login": datetime.now(timezone.utc).isoformat()}
        ).eq("id", user_row["id"]).execute()

        return self._issue_tokens(user_row)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_access_token(refresh_token)
        if payload is None or payload.get("type") != "refresh" or "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
            )

        result = (
            self.db.table(TABLE_NAME).select("*").eq("id", payload["sub"]).limit(1).execute()
        )
        if not result.data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        user_row = result.data[0]
        if not user_row.get("is_active", True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

        return self._issue_tokens(user_row)

    def _issue_tokens(self, user_row: dict) -> TokenResponse:
        user_id = str(user_row["id"])
        access_token = create_access_token(subject=user_id)
        refresh_token = create_refresh_token(subject=user_id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse(**user_row),
        )
