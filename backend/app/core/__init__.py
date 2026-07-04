# app/core/__init__.py
# =============================================================================
# CORE MODULE - Exports core functionality
# =============================================================================

import logging
from typing import Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import (
    # Database engine
    engine,
    # Session factory
    AsyncSessionLocal,
    # Dependency for FastAPI routes
    get_db,
    # Database lifecycle management
    init_db,
    close_db,
    # Status and health checks
    is_database_configured,
    get_db_status,
    check_db_health,
    # Context manager
    get_db_context,
)

logger = logging.getLogger(__name__)

# ─── ALIASES ──────────────────────────────────────────────────────

db = AsyncSessionLocal


# ─── CONVENIENCE FUNCTIONS ──────────────────────────────────────

def is_db_ready() -> bool:
    """Quick check if database is ready for use."""
    return is_database_configured()


def get_db_info() -> dict:
    """Get detailed database information for debugging."""
    return get_db_status()


# ─── PUBLIC API ──────────────────────────────────────────────────

__all__ = [
    "settings",
    "engine",
    "AsyncSessionLocal",
    "db",
    "get_db",
    "get_db_context",
    "init_db",
    "close_db",
    "is_database_configured",
    "is_db_ready",
    "get_db_status",
    "get_db_info",
    "check_db_health",
    "AsyncSession",
]


# ─── MODULE INITIALIZATION LOGGING ──────────────────────────────

def _log_core_status() -> None:
    """Log the status of core module components on import."""
    if settings.DEBUG:
        logger.debug("=" * 50)
        logger.debug("🔧 CORE MODULE INITIALIZED")
        logger.debug(f"   App: {settings.APP_NAME} v{settings.APP_VERSION}")
        logger.debug(f"   Environment: {settings.ENV}")
        logger.debug(f"   Debug: {settings.DEBUG}")
        logger.debug(f"   Database configured: {is_database_configured()}")
        logger.debug(f"   Engine created: {engine is not None}")
        logger.debug(f"   Session factory: {AsyncSessionLocal is not None}")
        logger.debug("=" * 50)
    else:
        logger.info(f"✅ Core module loaded - {settings.APP_NAME} v{settings.APP_VERSION}")

_log_core_status()


def get_module_doc() -> str:
    """Return module documentation."""
    return __doc__ or "Core module for AUTO-V API"


def get_exported_names() -> list:
    """Return list of all exported names."""
    return sorted(__all__)
