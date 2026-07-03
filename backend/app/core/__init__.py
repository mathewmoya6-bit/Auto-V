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

# Alias for backward compatibility if needed
db = AsyncSessionLocal

__all__ = [
    "settings",
    "engine",
    "AsyncSessionLocal",
    "db",
    "get_db",
    "init_db",
    "close_db",
    "is_database_configured",
    "get_db_status",
    "check_db_health",
]
