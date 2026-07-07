# app/core/__init__.py
# =============================================================================
# AUTO-V API - Core Package
# =============================================================================

from app.core.config import settings
from app.core.database import (
    init_supabase,
    get_supabase,
    get_admin_client,
    is_configured,
    get_db,
    get_db_admin,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    refresh_access_token,
)
from app.core.logging import get_logger, setup_logging

__all__ = [
    # Config
    "settings",
    
    # Database
    "init_supabase",
    "get_supabase",
    "get_admin_client",
    "is_configured",
    "get_db",
    "get_db_admin",
    
    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    "refresh_access_token",
    
    # Logging
    "get_logger",
    "setup_logging",
]
