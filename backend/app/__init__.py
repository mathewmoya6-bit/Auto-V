# app/__init__.py
# =============================================================================
# AUTO-V API - Application Package
# =============================================================================

"""
AUTO-V API - Professional Vehicle Valuation Engine

A FastAPI-based backend for vehicle valuation, inspection, and fleet management.
"""

__version__ = "3.1.0"
__author__ = "AUTO-V Team"
__description__ = "Professional Vehicle Valuation Engine API"

# Import main app for easy access
from app.main import app

__all__ = [
    "app",
    "__version__",
    "__author__",
    "__description__",
]
