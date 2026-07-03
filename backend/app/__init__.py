# backend/app/__init__.py
# =============================================================================
# AUTO-V API - Application Package
# =============================================================================
# This file marks the 'app' directory as a Python package.
# It exports core components and provides a clean import interface.
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
    Base,
)

# Package version - matches the API version
__version__ = settings.APP_VERSION

# Package metadata
__title__ = settings.APP_NAME
__description__ = "Professional Vehicle Valuation Engine API - Single Source of Truth"

# =============================================================================
# PUBLIC API - What gets imported with 'from app import *'
# =============================================================================

__all__ = [
    # Core components
    "settings",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    "close_db",
    "is_database_configured",
    "get_db_status",
    "check_db_health",
    "Base",
    # Metadata
    "__version__",
    "__title__",
    "__description__",
]

# =============================================================================
# MODULE DOCUMENTATION
# =============================================================================

def get_package_info() -> dict:
    """
    Get package information.
    
    Returns:
        dict: Package metadata
    """
    return {
        "name": __title__,
        "version": __version__,
        "description": __description__,
        "environment": settings.ENV,
        "debug": settings.DEBUG,
    }


def get_status() -> dict:
    """
    Get the current status of the application components.
    
    Returns:
        dict: Status of database and other components
    """
    return {
        "database": {
            "configured": is_database_configured(),
            "engine_created": engine is not None,
            "session_factory_created": AsyncSessionLocal is not None,
        },
        "environment": settings.ENV,
        "debug": settings.DEBUG,
    }


# =============================================================================
# LOGGING SETUP
# =============================================================================

import logging

logger = logging.getLogger(__name__)

# Log package initialization
logger.debug(f"✅ {__title__} v{__version__} package initialized")
logger.debug(f"📌 Environment: {settings.ENV}")
logger.debug(f"🔧 Debug mode: {settings.DEBUG}")
logger.debug(f"🗄️  Database configured: {is_database_configured()}")
