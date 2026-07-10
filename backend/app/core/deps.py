from typing import Optional
from fastapi import Depends
from supabase import Client
from app.core.database import get_supabase, get_admin_client
from app.core.security import get_current_user


def get_supabase_client() -> Client:
    """Dependency for Supabase client"""
    return get_supabase()


def get_admin_client_dep() -> Client:
    """Dependency for admin client"""
    return get_admin_client()


# Optional: Get current user ID helper
async def get_current_user_id(current_user = Depends(get_current_user)):
    return current_user.id
