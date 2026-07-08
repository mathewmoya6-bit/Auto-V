# app/core/database.py
# =============================================================================
# AUTO-V API - Supabase Client Factory
# =============================================================================
"""
This is the ONLY data-access layer in the app. There is no ORM, no SQLAlchemy
session, no models/ package. Every service talks to Supabase through one of
the two clients below.

    get_supabase()     -> anon key, respects Row Level Security.
                           Safe default for reads where RLS policies
                           already express the access rules you want.

    get_admin_client() -> service-role key, BYPASSES Row Level Security.
                           Use for all backend-initiated writes, since this
                           API does its own authorization via JWT
                           (see app.core.security.get_current_user) rather
                           than relying on Supabase RLS to gate requests.

If a write ever goes through get_supabase() instead of get_admin_client(),
you will get: "new row violates row-level security policy" — that error
means the wrong client was used, not a policy misconfiguration.
"""
import logging
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase() -> Client:
    """Anon-key client. Reads only, RLS-respecting."""
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    logger.info("✅ Supabase client initialized (anon)")
    return client


@lru_cache
def get_admin_client() -> Client:
    """Service-role client. Bypasses RLS — backend writes only."""
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    logger.info("✅ Supabase client initialized (admin/service-role)")
    return client
