# app/core/deps.py
# =============================================================================
# AUTO-V API - Shared Dependencies
# =============================================================================
"""
Reusable FastAPI dependencies. `get_current_user` is what every protected
route should depend on — it validates the bearer token against Supabase
and returns the authenticated user, or raises 401.
"""
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.supabase_client import supabase_anon

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """
    Validates the Authorization: Bearer <token> header against Supabase
    and returns the Supabase user object. Use as a route dependency:

        @router.get("/protected")
        async def protected_route(user = Depends(get_current_user)):
            ...
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        result = supabase_anon.auth.get_user(token)
    except Exception as exc:
        logger.warning(f"Token validation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = result.user if result else None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
