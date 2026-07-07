# app/services/supabase_service.py
# =============================================================================
# AUTO-V API - Supabase Service (thin re-export layer)
# =============================================================================
# The real Supabase auth implementation lives in app/core/supabase.py.
# This module exists only because app/services/__init__.py and
# app/api/v1/routes/auth.py import from here. Rather than duplicating
# logic a third time, we re-export the real functions and wrap them in a
# service class for callers that expect a SupabaseService instance.

from app.core.supabase import (
    sign_up_user,
    sign_in_user,
    sign_out_user,
    get_user_by_token,
    refresh_access_token,
    reset_password,
    update_user_metadata,
    get_supabase,
    get_admin_client,
    is_supabase_configured,
)

__all__ = [
    "sign_up_user",
    "sign_in_user",
    "sign_out_user",
    "get_user_by_token",
    "refresh_access_token",
    "reset_password",
    "update_user_metadata",
    "SupabaseService",
]


class SupabaseService:
    """
    Class wrapper around the real Supabase auth functions in
    app/core/supabase.py, for modules that expect a service instance
    rather than standalone functions.
    """

    def __init__(self):
        self.client = get_supabase()

    async def sign_up(self, email: str, password: str, metadata: dict = None) -> dict:
        return await sign_up_user(email, password, metadata)

    async def sign_in(self, email: str, password: str) -> dict:
        return await sign_in_user(email, password)

    async def sign_out(self, access_token: str) -> dict:
        return await sign_out_user(access_token)

    async def get_user(self, token: str):
        return await get_user_by_token(token)

    async def refresh_token(self, refresh_token: str) -> dict:
        return await refresh_access_token(refresh_token)

    async def reset_user_password(self, email: str) -> dict:
        return await reset_password(email)

    async def update_metadata(self, user_id: str, metadata: dict) -> dict:
        return await update_user_metadata(user_id, metadata)

    def table(self, name: str):
        """Passthrough to the underlying Supabase client's table/query builder."""
        return self.client.table(name)

    @property
    def is_configured(self) -> bool:
        return is_supabase_configured()
