# app/core/deps.py
#
# Shared FastAPI dependencies for route files, primarily authentication.
#
# ASSUMPTION (flagging clearly): the frontend authenticates directly
# against Supabase Auth (see supabase.js — signInWithPassword, etc.)
# and would send that session's access_token to this backend, e.g.
# as `Authorization: Bearer <token>`. This backend verifies that same
# token using SUPABASE_JWT_SECRET (found in Supabase dashboard under
# Project Settings → API → JWT Settings) rather than maintaining a
# separate login system. If instead this backend is meant to issue
# its OWN tokens independently of Supabase Auth, this file needs a
# different approach (e.g. python-jose + your own secret + a /login
# route that checks password_hash) — tell me if that's the case.

from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import UserProfile

bearer_scheme = HTTPBearer(auto_error=False)


def decode_supabase_jwt(token: str) -> dict:
    if not settings.SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET is not configured on the server",
        )
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_supabase_jwt(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject claim")

    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Token is valid (they're a real Supabase-authenticated user) but
        # no matching profile row exists yet — mirrors the same gap that
        # caused the 500/PGRST116 errors on the admin login page earlier.
        # Auto-provisioning here rather than 404ing keeps this backend
        # resilient to that same class of drift.
        user = UserProfile(id=user_id, email=payload.get("email", ""))
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    return user


async def require_admin(user: UserProfile = Depends(get_current_user)) -> UserProfile:
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user
