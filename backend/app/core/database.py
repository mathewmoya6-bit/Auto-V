from functools import lru_cache
from supabase import create_client, Client
from app.core.config import settings


@lru_cache
def get_supabase() -> Client:
    """Get Supabase client with anon key"""
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key
    )


@lru_cache
def get_admin_client() -> Client:
    """Get Supabase admin client with service role key"""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key
    )


# Singleton instances
supabase = get_supabase()
admin = get_admin_client()
