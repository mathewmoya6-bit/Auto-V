# app/schemas/mileage.py
# =============================================================================
# AUTO-V API - Mileage Schemas
# =============================================================================
"""
Assumes Supabase tables: vehicle_categories, vehicle_variants, routes,
mileage_claims — column names below match the pre-existing schema this
was consolidated from (see git history), which was verified against
real usage in calculate.py.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_camel(snake: str) -> str:
    head, *tail = snake.split("_")
    return head + "".join(part.title() for part in tail)


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


# ─── Vehicle Category ───────────────────────────────────────────────

class VehicleCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    fuel_type: Optional[str] = None
    is_active: bool = True


# ─── Vehicle Variant (rates + components + 5yr costs) ───────────────

class VehicleVariantResponse(BaseModel):
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
    components: Dict[str, float] = {}
    is_active: bool = True


# ─── Route ────────────────────────────────────────────────────────────

class RouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    from_city: str
    to_city: str
    km: float
    is_active: bool = True


# ─── Trip cost calculation (POST /mileage/calculate) ────────────────

class MileageCalculateRequest(_CamelModel):
    variant_id: UUID = Field(..., description="vehicle_variants.id to price out")
    distance: float = Field(..., gt=0, le=100_000, description="Trip distance in kilometers")
    include_forecast: bool = False
    include_comparison: bool = False

    @field_validator("distance")
    @classmethod
    def distance_must_be_finite(cls, v: float) -> float:
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("distance must be a finite number")
        return v


class MileageCalculateResponse(_CamelModel):
    currency: str = "KES"
    calculation_version: str = "2.0"
    total_cost: float
    fixed_cost: float
    operating_cost: float
    total_rate: float
    fixed_rate: float
    operating_rate: float
    components: Dict[str, float] = Field(default_factory=dict)
    yearly: Dict[str, float] = Field(default_factory=dict)
    initial_cost: float
    method: str = "supabase"
    distance: float
    forecast: Optional[Dict[str, float]] = None
    comparison: Optional[Dict[str, Any]] = None


# ─── Mileage Claim ────────────────────────────────────────────────────

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


class MileageClaimUpdate(BaseModel):
    trip_date: Optional[date] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    distance_km: Optional[float] = None
    vehicle_category: Optional[str] = None
    rate_per_km: Optional[float] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None
    odometer_start: Optional[int] = None
    odometer_end: Optional[int] = None
    status: Optional[str] = None


class MileageClaimResponse(BaseModel):
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
    status: str = "pending"
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class MileageApprovalRequest(BaseModel):
    approve: bool
    comments: Optional[str] = None


class MileageClaimSummary(BaseModel):
    total_claims: int
    total_distance_km: float
    total_claim_amount: float
    pending_claims: int
    approved_claims: int
    rejected_claims: int
