# app/core/__init__.py
# =============================================================================
# CORE MODULE - Exports config, database, and security utilities
# =============================================================================

from app.core.config import settings
from app.core.database import (
    Base,
    engine,
    AsyncSessionLocal,
    get_db,
    get_db_context,
    init_db,
    close_db,
    check_db_health,
    is_database_configured,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

__all__ = [
    "settings",
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "get_db_context",
    "init_db",
    "close_db",
    "check_db_health",
    "is_database_configured",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
]
