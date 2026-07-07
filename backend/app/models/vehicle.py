# app/models/vehicle.py
# =============================================================================
# AUTO-V API - Vehicle & Scan Models (Pydantic Native)
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class VehicleImage(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    vehicle_id: uuid.UUID
    image_url: str
    is_primary: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


class VINScan(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    vin: str
    raw_response: Optional[dict] = None
    status: str = "pending"  # pending, success, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


class Vehicle(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID  # Matches UserProfile.id
    make: str
    model: str
    year: int
    license_plate: str
    vin: Optional[str] = None
    color: Optional[str] = None
    current_odometer: float = 0.0
    status: str = "active"
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}
