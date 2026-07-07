# backend/app/models/__init__.py
# =============================================================================
# AUTO-V API - Models Registry (Single Source of Truth)
# =============================================================================

# Use absolute package paths instead of relative dots (.)
from app.models.user import UserProfile
from app.models.vehicle import Vehicle, VehicleImage, VINScan
from app.models.valuation import Valuation
from app.models.inspection import Inspection
from app.models.certificate import Certificate
from app.models.fleet import Fleet
from app.models.payment import Payment
from app.models.mileage import (
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
