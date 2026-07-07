# app/api/__init__.py
# =============================================================================
# AUTO-V API - API Package
# =============================================================================

"""
API package containing all versioned API routers.
"""

from app.api.v1 import api_router

__all__ = [
    "api_router",
]
