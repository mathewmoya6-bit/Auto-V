# app/core/__init__.py
# =============================================================================
# CORE MODULE - Exports core functionality
# =============================================================================

from app.core.config import settings
from app.core.database import (
    engine,
    AsyncSessionLocal,
    get_db,
    init_db,
    close_db,
    is_database_configured,
    get_db_status,
    check_db_health,
)

# If you want to keep 'db' as an alias for the session factory:
db = AsyncSessionLocal

__all__ = [
    "settings",
    "engine",
    "AsyncSessionLocal",
    "db",  # Alias for AsyncSessionLocal
    "get_db",
    "init_db",
    "close_db",
    "is_database_configured",
    "get_db_status",
    "check_db_health",
]
