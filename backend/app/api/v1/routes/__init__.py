# app/api/v1/routes/__init__.py
# =============================================================================
# AUTO-V API - Routes Package (Version 1)
# =============================================================================
"""
This package contains all route modules for the AUTO-V API v1.
Each module handles a specific domain/resource.

Add one line here per domain, only once that domain's route file exists
and its own imports are verified. Do not import services or schemas here —
this file only ever imports route modules.
"""
from . import auth
from . import users
from . import categories
from . import vehicles
from . import mileage
from . import instant_value
from . import vehicle_assessments
from . import valuations
from . import payments
from . import inspections
from . import reports
from . import settings

__all__ = [
    "auth",
    "users",
    "categories",
    "vehicles",
    "mileage",
    "instant_value",
    "vehicle_assessments",
    "valuations",
    "payments",
    "inspections",
    "reports",
    "settings"
]
