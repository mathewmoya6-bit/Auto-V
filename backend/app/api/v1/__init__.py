# app/api/v1/routes/__init__.py
# =============================================================================
# AUTO-V API - Routes Package
# =============================================================================

from . import auth
from . import mileage
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
