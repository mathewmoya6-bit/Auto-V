# app/services/supabase_service.py
# =============================================================================
# AUTO-V API - Supabase Auth Service
# =============================================================================
import os
from typing import Optional
from supabase import create_client, Client
# NOTE: verify these env var names against your actual Render/.env config.
# Common alternatives: SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY.
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL or SUPABASE_KEY environment variables. "
        "Check your Render environment settings."
    )
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
async def sign_up_user(email: str, password: str, metadata: Optional[dict] = None) -> dict:
    """
    Register a new user via Supabase Auth.
    Returns: {"success": bool, "user": dict | None, "error": str | None}
    """
    try:
        response = supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {"data": metadata or {}},
            }
        )
        if response.user is None:
            return {"success": False, "error": "Registration failed", "user": None}
        return {
            "success": True,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                **(metadata or {}),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e), "user": None}
async def sign_in_user(email: str, password: str) -> dict:
    """
    Sign in an existing user via Supabase Auth.
    Returns: {"success": bool, "user": dict | None, "session": dict | None}
    """
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        if response.user is None or response.session is None:
            return {"success": False, "error": "Invalid credentials", "user": None, "session": None}
        return {
            "success": True,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
            },
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e), "user": None, "session": None}
async def get_user_by_token(token: str) -> Optional[dict]:
    """
    Validate a bearer token and return the associated user, or None if invalid.
    """
    try:
        response = supabase.auth.get_user(token)
        if response.user is None:
            return None
        return {
            "id": response.user.id,
            "email": response.user.email,
        }
    except Exception:
        return None


class SupabaseService:
    """
    Class wrapper exposing the Supabase client and auth helpers, for modules
    that depend on a service instance rather than standalone functions.

    NOTE: This class's surface is a best-effort guess. If other files call
    methods on SupabaseService beyond what's here, you'll get an
    AttributeError naming the missing method — add it here matching the
    same pattern.
    """

    def __init__(self):
        self.client = supabase

    async def sign_up(self, email: str, password: str, metadata: Optional[dict] = None) -> dict:
        return await sign_up_user(email, password, metadata)

    async def sign_in(self, email: str, password: str) -> dict:
        return await sign_in_user(email, password)

    async def get_user(self, token: str) -> Optional[dict]:
        return await get_user_by_token(token)

    def table(self, name: str):
        """Passthrough to the underlying Supabase client's table/query builder."""
        return self.client.table(name)
