# app/models/__init__.py
# =============================================================================
# AUTO-V API - Models Registry (Single Source of Truth)
# =============================================================================

from app.core.database import Base

# Import all models in the correct order (dependencies first)
from .user import UserProfile
from .vehicle import Vehicle, VehicleImage, VINScan
from .mileage import (
    VehicleCategory,
    VehicleVariant,
    Route,
    MileageClaim,
)

__all__ = [
    "Base",
    "UserProfile",
    "Vehicle",
    "VehicleImage",
    "VINScan",
    "VehicleCategory",
    "VehicleVariant",
    "Route",
    "MileageClaim",
]
