"""
Mileage Schemas
Pydantic models for vehicle mileage tracking and claims
"""

from datetime import date, datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, validator


class CategoryOut(BaseModel):
    """Category/vehicle type output schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str = Field(..., description="Vehicle category name (e.g., Sedan, SUV, Truck)")
    fuel_type: Optional[str] = Field(None, description="Fuel type: Petrol, Diesel, Electric, Hybrid")
    is_active: bool = Field(default=True)


class VariantOut(BaseModel):
    """Vehicle variant output schema with detailed cost breakdown"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    label: str = Field(..., description="Variant label/name")

    # Per-kilometer costs
    fixed_per_km: float = Field(..., ge=0, description="Fixed cost per kilometer")
    operating_per_km: float = Field(..., ge=0, description="Operating cost per kilometer")
    total_per_km: float = Field(..., ge=0, description="Total cost per kilometer")

    # Year-by-year costs
    initial_cost: float = Field(..., ge=0, description="Initial purchase cost")
    year1: float = Field(..., ge=0, description="Year 1 total cost")
    year2: float = Field(..., ge=0, description="Year 2 total cost")
    year3: float = Field(..., ge=0, description="Year 3 total cost")
    year4: float = Field(..., ge=0, description="Year 4 total cost")
    year5: float = Field(..., ge=0, description="Year 5 total cost")

    # Component breakdown (per-km values)
    # Keys: Insurance, Depreciation, Interest, Fuel, Servicing, Repairs, Tyres, Licences
    components: Dict[str, float] = Field(
        default_factory=dict,
        description="Detailed cost components per kilometer"
    )

    is_active: bool = Field(default=True)


class RouteOut(BaseModel):
    """Route information output schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_city: str = Field(..., description="Starting city")
    to_city: str = Field(..., description="Destination city")
    km: float = Field(..., ge=0, description="Distance in kilometers")
    is_active: bool = Field(default=True)


class MileageClaimOut(BaseModel):
    """Mileage claim output schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID = Field(..., description="User who submitted the claim")
    vehicle_id: Optional[UUID] = Field(None, description="Vehicle used")

    # Trip details
    trip_date: date = Field(..., description="Date of the trip")
    start_location: Optional[str] = Field(None, description="Starting location")
    end_location: Optional[str] = Field(None, description="Ending location")
    distance_km: Optional[float] = Field(None, ge=0, description="Distance traveled")
    
    # Cost details
    vehicle_category: Optional[str] = Field(None, description="Category of vehicle used")
    rate_per_km: Optional[float] = Field(None, ge=0, description="Rate per kilometer")
    claim_amount: Optional[float] = Field(None, ge=0, description="Total claim amount")
    
    # Additional information
    purpose: Optional[str] = Field(None, description="Purpose of the trip")
    notes: Optional[str] = Field(None, description="Additional notes")

    # Odometer readings
    odometer_start: Optional[int] = Field(None, ge=0, description="Starting odometer reading")
    odometer_end: Optional[int] = Field(None, ge=0, description="Ending odometer reading")

    # Approval status
    status: str = Field(..., description="Claim status: pending, approved, rejected")
    approved_by: Optional[UUID] = Field(None, description="User who approved the claim")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class MileageClaimCreate(BaseModel):
    """Mileage claim creation schema"""
    vehicle_id: Optional[UUID] = Field(None, description="Vehicle used (optional)")
    trip_date: date = Field(..., description="Date of the trip")
    start_location: Optional[str] = Field(None, description="Starting location")
    end_location: Optional[str] = Field(None, description="Ending location")
    distance_km: float = Field(..., ge=0, description="Distance traveled in kilometers")
    vehicle_category: Optional[str] = Field(None, description="Category of vehicle used")
    rate_per_km: float = Field(..., ge=0, description="Rate per kilometer")
    purpose: Optional[str] = Field(None, description="Purpose of the trip")
    notes: Optional[str] = Field(None, description="Additional notes")
    odometer_start: Optional[int] = Field(None, ge=0, description="Starting odometer reading")
    odometer_end: Optional[int] = Field(None, ge=0, description="Ending odometer reading")


class MileageClaimUpdate(BaseModel):
    """Mileage claim update schema"""
    trip_date: Optional[date] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    distance_km: Optional[float] = Field(None, ge=0)
    vehicle_category: Optional[str] = None
    rate_per_km: Optional[float] = Field(None, ge=0)
    purpose: Optional[str] = None
    notes: Optional[str] = None
    odometer_start: Optional[int] = Field(None, ge=0)
    odometer_end: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, description="Update status: approved, rejected, pending")


class MileageClaimSummary(BaseModel):
    """Summary statistics for mileage claims"""
    total_claims: int = Field(..., ge=0)
    total_distance_km: float = Field(..., ge=0)
    total_claim_amount: float = Field(..., ge=0)
    pending_claims: int = Field(..., ge=0)
    approved_claims: int = Field(..., ge=0)
    rejected_claims: int = Field(..., ge=0)
    
    # Optional time period breakdown
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    
    # Category breakdown
    by_category: Optional[Dict[str, Dict[str, float]]] = Field(
        None,
        description="
