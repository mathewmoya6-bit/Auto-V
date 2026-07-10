"""
API Package - AUTO-V API Routes

This package contains all API route definitions for the AUTO-V application.
Routes are organized by version (v1, v2, etc.) and follow RESTful conventions.
"""

from .v1 import api_router as v1_router

__all__ = [
    "v1_router",
]
