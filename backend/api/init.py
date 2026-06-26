"""
Core Package
"""

from app.core.config import settings
from app.core.security import security
from app.core.database import supabase, get_supabase, get_supabase_status, check_supabase_health
from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.auth_middleware import (
    generate_token,
    generate_access_token,
    generate_refresh_token,
    generate_token_pair,
    verify_token,
    verify_access_token,
    verify_refresh_token,
    JWTBearer,
    require_auth,
    require_role,
    get_user_id_from_token,
    get_user_email_from_token,
    get_user_role_from_token,
    is_token_valid,
    refresh_token,
)

__all__ = [
    "settings",
    "security",
    "supabase",
    "get_supabase",
    "get_supabase_status",
    "check_supabase_health",
    "get_current_user",
    "get_current_user_optional",
    "generate_token",
    "generate_access_token",
    "generate_refresh_token",
    "generate_token_pair",
    "verify_token",
    "verify_access_token",
    "verify_refresh_token",
    "JWTBearer",
    "require_auth",
    "require_role",
    "get_user_id_from_token",
    "get_user_email_from_token",
    "get_user_role_from_token",
    "is_token_valid",
    "refresh_token",
]
