# app/models/mileage.py
# =============================================================================
# AUTO-V API - Mileage & Claims Models (Pydantic Native)
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class VehicleCategory(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str  # e.g., "Sedan", "SUV", "Heavy Truck"
    description: Optional[str] = None
    base_rate_per_km: float

    model_config = {"from_attributes": True}


class VehicleVariant(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    category_id: uuid.UUID
    make: str
    model: str
    year: int
    fuel_efficiency_city: Optional[float] = None
    fuel_efficiency_hwy: Optional[float] = None

    model_config = {"from_attributes": True}


class Route(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    start_location: str
    end_location: str
    estimated_distance_km: float
    waypoints: Optional[dict] = None  # GeoJSON tracking payload

    model_config = {"from_attributes": True}


class MileageClaim(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    vehicle_id: uuid.UUID
    route_id: Optional[uuid.UUID] = None
    
    purpose: str
    start_odometer: float
    end_odometer: float
    total_distance_km: float
    calculated_reimbursement: float
    
    status: str = "submitted"  # submitted, approved, rejected
    approved_by: Optional[uuid.UUID] = None
    rejection_reason: Optional[str] = None
    
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
