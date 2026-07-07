# app/services/auth_service.py
# =============================================================================
# AUTO-V API - Auth Service
# =============================================================================
from app.services.supabase_service import (
    sign_up_user,
    sign_in_user,
    get_user_by_token,
)


class AuthService:
    """
    Thin wrapper around Supabase auth functions, exposed as a service class
    so routes can depend on `AuthService` rather than importing individual
    functions directly.
    """

    @staticmethod
    async def sign_up(email: str, password: str, **kwargs):
        return await sign_up_user(email, password, **kwargs)

    @staticmethod
    async def sign_in(email: str, password: str, **kwargs):
        return await sign_in_user(email, password, **kwargs)

    @staticmethod
    async def get_current_user(token: str):
        return await get_user_by_token(token)
