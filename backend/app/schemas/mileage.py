# app/schemas/mileage.py
# =============================================================================
# AUTO-V API - Response schemas (mirror app/models/mileage.py exactly)
# =============================================================================

from datetime import date, datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    fuel_type: Optional[str] = None
    is_active: bool


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    label: str

    fixed_per_km: float
    operating_per_km: float
    total_per_km: float

    initial_cost: float
    year1: float
    year2: float
    year3: float
    year4: float
    year5: float

    # Expected keys: Insurance, Depreciation, Interest, Fuel, Servicing,
    # Repairs, Tyres, Licences (per-km values) -- matches the frontend's
    # detailMap and the seed data in mileage_schema.sql.
    components: Dict[str, float] = {}

    is_active: bool


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_city: str
    to_city: str
    km: float
    is_active: bool


class MileageClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    vehicle_id: Optional[UUID] = None

    trip_date: date
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    distance_km: Optional[float] = None
    vehicle_category: Optional[str] = None
    rate_per_km: Optional[float] = None
    claim_amount: Optional[float] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None

    odometer_start: Optional[int] = None
    odometer_end: Optional[int] = None

    status: str
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class MileageClaimCreate(BaseModel):
    vehicle_id: Optional[UUID] = None
    trip_date: date
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    distance_km: float
    vehicle_category: Optional[str] = None
    rate_per_km: float
    purpose: Optional[str] = None
    notes: Optional[str] = None
    odometer_start: Optional[int] = None
    odometer_end: Optional[int] = None
