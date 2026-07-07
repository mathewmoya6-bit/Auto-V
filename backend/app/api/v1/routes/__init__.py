# app/api/v1/routes/__init__.py
# =============================================================================
# AUTO-V API - Routes Package (Version 1)
# =============================================================================

"""
Route modules for API Version 1.

Each module contains related endpoints grouped by domain.
"""

# ─── Import all route modules ─────────────────────────────────────────

from . import auth
from . import mileage
from . import vehicles
from . import valuations
from . import inspections
from . import certificates
from . import payments
from . import fleets
from . import dashboard
from . import admin
from . import webhooks
from . import reports
from . import settings

# ─── Export all routers ──────────────────────────────────────────────

__all__ = [
    "auth",
    "mileage",
    "vehicles",
    "valuations",
    "inspections",
    "certificates",
    "payments",
    "fleets",
    "dashboard",
    "admin",
    "webhooks",
    "reports",
    "settings",
]

# ─── Module Information ─────────────────────────────────────────────

__version__ = "1.0.0"
__description__ = "AUTO-V API V1 Routes"

# ─── Optional: Route Count ──────────────────────────────────────────

def get_route_count() -> int:
    """Get the total number of route modules."""
    return len(__all__)
