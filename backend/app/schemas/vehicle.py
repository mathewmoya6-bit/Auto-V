# app/schemas/vehicle.py
# =============================================================================
# AUTO-V API - Vehicle Schemas
# =============================================================================
"""
Assumes a Supabase table `vehicles` with columns matching VehicleResponse
below. owner_id is set server-side from the authenticated user — never
accepted from the client (see VehicleCreate).
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VehicleCreate(BaseModel):
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1900, le=datetime.now().year + 1)
    vin: Optional[str] = Field(None, min_length=11, max_length=17)
    registration_number: Optional[str] = None
    mileage: Optional[int] = Field(None, ge=0, le=2_000_000)
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    color: Optional[str] = None
    condition: Optional[str] = Field("good", pattern="^(excellent|good|fair|poor|salvage)$")


class VehicleUpdate(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    vin: Optional[str] = None
    registration_number: Optional[str] = None
    mileage: Optional[int] = Field(None, ge=0, le=2_000_000)
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    color: Optional[str] = None
    condition: Optional[str] = Field(None, pattern="^(excellent|good|fair|poor|salvage)$")


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    make: str
    model: str
    year: int
    vin: Optional[str] = None
    registration_number: Optional[str] = None
    mileage: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    color: Optional[str] = None
    condition: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
