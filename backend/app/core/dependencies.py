"""
FastAPI Dependencies
"""

from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.auth_middleware import (
    verify_access_token,
    get_current_user as _get_current_user,
    get_current_user_optional as _get_current_user_optional
)

security_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    """
    Get current user from JWT token.
    Validates token and returns user data.
    """
    return await _get_current_user(credentials)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
):
    """
    Get current user if authenticated, otherwise None.
    """
    return await _get_current_user_optional(credentials)


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current active user with additional validation.
    """
    # Add additional validation here (e.g., check database for active status)
    return current_user


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current admin user. Requires admin role.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user
