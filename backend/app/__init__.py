# app/__init__.py
# =============================================================================
# AUTO-V API - Application Package
# =============================================================================

from app.core.config import settings
from app.core.database import (
    engine,
    AsyncSessionLocal,
    get_db,
    get_db_context,
    init_db,
    close_db,
    is_database_configured,
    get_db_status,
    check_db_health,
    Base,
)

__version__ = settings.APP_VERSION
__title__ = settings.APP_NAME

__all__ = [
    "settings",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "get_db_context",
    "init_db",
    "close_db",
    "is_database_configured",
    "get_db_status",
    "check_db_health",
    "Base",
    "__version__",
    "__title__",
]
