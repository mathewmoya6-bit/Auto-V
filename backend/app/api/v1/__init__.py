# app/api/v1/__init__.py
# =============================================================================
# AUTO-V API - Version 1
# =============================================================================

"""
API Version 1 - Current stable version.

This module aggregates all v1 routes and provides the main API router.
"""

from app.api.v1.api import api_router

# Version information
VERSION = "1.0.0"
DESCRIPTION = "AUTO-V API Version 1 - Production Stable"

__all__ = [
    "api_router",
    "VERSION",
    "DESCRIPTION",
]
