# app/models/__init__.py

from app.core.database import Base
from app.models.user import UserProfile
from app.models.mileage import VehicleCategory, VehicleVariant, Route

__all__ = [
    "Base",
    "UserProfile",
    "VehicleCategory",
    "VehicleVariant",
    "Route",
]
