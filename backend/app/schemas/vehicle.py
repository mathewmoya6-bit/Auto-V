# app/schemas/vehicle.py
# =============================================================================
# AUTO-V API - Vehicle Schemas
# =============================================================================
# NOTE: field names are a best-effort guess based on typical vehicle
# valuation data. Verify against your actual Vehicle/VehicleImage/VINScan
# models (app/models/vehicle.py) and adjust field names/types to match.

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class VehicleCreate(BaseModel):
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
    owner_id: Optional[UUID] = None


class VehicleUpdate(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    vin: Optional[str] = None
    registration_number: Optional[str] = None
    mileage: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    color: Optional[str] = None
    condition: Optional[str] = None


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
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
    owner_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VehicleImageCreate(BaseModel):
    vehicle_id: UUID
    image_url: str
    caption: Optional[str] = None
    is_primary: bool = False


class VehicleImage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    image_url: str
    caption: Optional[str] = None
    is_primary: bool = False
    created_at: Optional[datetime] = None


class VINScanCreate(BaseModel):
    vin: str
    vehicle_id: Optional[UUID] = None
    image_url: Optional[str] = None


class VINScan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vin: str
    vehicle_id: Optional[UUID] = None
    image_url: Optional[str] = None
    decoded_make: Optional[str] = None
    decoded_model: Optional[str] = None
    decoded_year: Optional[int] = None
    created_at: Optional[datetime] = None


class VINScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vin: str
    vehicle_id: Optional[UUID] = None
    decoded_make: Optional[str] = None
    decoded_model: Optional[str] = None
    decoded_year: Optional[int] = None
    success: bool = True
    message: Optional[str] = None
    created_at: Optional[datetime] = None
