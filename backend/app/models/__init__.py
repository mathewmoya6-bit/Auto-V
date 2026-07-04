# app/models/__init__.py
# =============================================================================
# AUTO-V API - Models package
# =============================================================================
from app.core.database import Base

from app.models.user import UserProfile
from app.models.vehicle import Vehicle, VehicleImage, VINScan
from app.models.valuation import Valuation
from app.models.inspection import Inspection
from app.models.mileage import VehicleCategory, VehicleVariant, Route, MileageClaim
from app.models.fleet import Fleet, FleetVehicle, FleetDriver
from app.models.certificate import Certificate
from app.models.payment import Payment

__all__ = [
    "Base",
    "UserProfile",
    "Vehicle", "VehicleImage", "VINScan",
    "Valuation",
    "Inspection",
    "VehicleCategory", "VehicleVariant", "Route", "MileageClaim",
    "Fleet", "FleetVehicle", "FleetDriver",
    "Certificate",
    "Payment",
]
