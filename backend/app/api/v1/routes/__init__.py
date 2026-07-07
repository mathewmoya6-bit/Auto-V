# app/api/v1/routes/__init__.py
# =============================================================================
# AUTO-V API - Routes Package
# =============================================================================

# Import routes here so they can be imported from app.api.v1.routes
from . import auth
from . import mileage

# Uncomment as you add more routes
# from . import vehicles
# from . import inspections
# from . import valuations
# from . import fleets
# from . import certificates
# from . import payments

__all__ = [
    "auth",
    "mileage",
    # "vehicles",
    # "inspections",
    # "valuations",
    # "fleets",
    # "certificates",
    # "payments",
]
