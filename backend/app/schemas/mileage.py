"""
Mileage Schemas - NO circular imports
"""

from datetime import date, datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    fuel_type: Optional[str] = None
    is_active: bool = True


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
    components: Dict[str, float] = {}
    is_active: bool = True


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    from_city: str
    to_city: str
    km: float
    is_active: bool = True


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


class MileageClaimSummary(BaseModel):
    total_claims: int
    total_distance_km: float
    total_claim_amount: float
    pending_claims: int
    approved_claims: int
    rejected_claims: int
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    by_category: Optional[Dict[str, Dict[str, float]]] = None
    monthly_trend: Optional[Dict[str, Dict[str, float]]] = None


class VehicleRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category_id: UUID
    category_name: str
    variant_id: UUID
    variant_label: str
    rate_per_km: float
    effective_date: date
    is_active: bool = True


class MileageApprovalRequest(BaseModel):
    claim_id: UUID
    approve: bool
    comments: Optional[str] = None
    approved_by: UUID
