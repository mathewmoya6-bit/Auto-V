# app/models/__init__.py
# =============================================================================
# AUTO-V API - Models Registry (Single Source of Truth)
# =============================================================================

# Import all models in the correct order
from .user import UserProfile
from .vehicle import Vehicle, VehicleImage, VINScan
from .valuation import Valuation
from .inspection import Inspection
from .certificate import Certificate
from .fleet import Fleet
from .payment import Payment
from .mileage import (
    VehicleCategory,
    VehicleVariant,
    Route,
    MileageClaim,
)

__all__ = [
    "UserProfile",
    "Vehicle",
    "VehicleImage",
    "VINScan",
    "Valuation",
    "Inspection",
    "Certificate",
    "Fleet",
    "Payment",
    "VehicleCategory",
    "VehicleVariant",
    "Route",
    "MileageClaim",
]
