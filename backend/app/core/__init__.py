# app/core/__init__.py
# =============================================================================
# CORE MODULE - Exports core functionality
# =============================================================================
# This module serves as the central export point for all core functionality:
# - Configuration settings
# - Database engine and session management
# - Database initialization and cleanup
# - Health checks and status utilities
#
# Usage:
#   from app.core import settings, get_db, init_db
#   from app.core import db  # AsyncSessionLocal alias
#
# Example routes:
#   @router.get("/items")
#   async def get_items(db: AsyncSession = Depends(get_db)):
#       ...
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

# =============================================================================
# SETUP LOGGING
# =============================================================================

logger = logging.getLogger(__name__)

# =============================================================================
# ALIASES FOR BACKWARD COMPATIBILITY
# =============================================================================
# 'db' is an alias for AsyncSessionLocal - used when you need direct access
# to the session factory without going through the dependency injection.
#
# Example:
#   from app.core import db
#   async with db() as session:
#       result = await session.execute(...)
db = AsyncSessionLocal

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def is_db_ready() -> bool:
    """
    Quick check if database is ready for use.
    
    Returns:
        True if database is configured and engine is created, False otherwise.
    
    Example:
        if is_db_ready():
            await init_db()
        else:
            logger.warning("Database not ready")
    """
    return is_database_configured()


def get_db_info() -> dict:
    """
    Get detailed database information for debugging.
    
    Returns:
        Dictionary with database configuration and status information.
    
    Example:
        info = get_db_info()
        print(f"Database: {info['configured']}, Engine: {info['engine_created']}")
    """
    return get_db_status()


# =============================================================================
# PUBLIC API - What this module exports
# =============================================================================

__all__ = [
    # Configuration
    "settings",
    
    # Database engine and session
    "engine",
    "AsyncSessionLocal",
    "db",  # ← Alias for AsyncSessionLocal (fixes ImportError)
    
    # Database dependency and lifecycle
    "get_db",
    "get_db_context",
    "init_db",
    "close_db",
    
    # Status and health
    "is_database_configured",
    "is_db_ready",
    "get_db_status",
    "get_db_info",
    "check_db_health",
    
    # Types
    "AsyncSession",
]

# =============================================================================
# MODULE INITIALIZATION LOGGING
# =============================================================================

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
        # Minimal logging in production
        logger.info(f"✅ Core module loaded - {settings.APP_NAME} v{settings.APP_VERSION}")


# Log core module status on import
_log_core_status()

# =============================================================================
# RE-EXPORT TYPES FOR TYPE HINTING
# =============================================================================

# This allows users to import AsyncSession from app.core for type hints
# Example:
#   from app.core import AsyncSession
#   async def my_func(session: AsyncSession):
#       ...

# Note: AsyncSession is already imported from sqlalchemy.ext.asyncio above

# =============================================================================
# MODULE DOCUMENTATION
# =============================================================================

def get_module_doc() -> str:
    """Return module documentation."""
    return __doc__ or "Core module for AUTO-V API"


def get_exported_names() -> list:
    """Return list of all exported names."""
    return sorted(__all__)
