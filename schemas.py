# app/schemas/instant_value.py
"""
Pydantic schemas for the Instant Value module.

Instant Value is a lightweight, "no full vehicle record required" estimate —
think of it as the quick lead-gen calculator vs. the full Valuation module,
which presumably operates on an existing Vehicle row.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class VehicleCondition(str, Enum):
    excellent = "excellent"
    good = "good"
    fair = "fair"
    poor = "poor"


class InstantValueRequest(BaseModel):
    make: str = Field(..., examples=["Toyota"])
    model: str = Field(..., examples=["Corolla"])
    year: int = Field(..., ge=1970, le=2100)
    mileage: int = Field(..., ge=0, description="Current odometer reading, km")
    condition: VehicleCondition = VehicleCondition.good
    category_id: Optional[UUID] = Field(
        None, description="Optional link to an existing VehicleCategory"
    )
    location: Optional[str] = Field(None, description="City/region, affects market adj.")


class ValueFactor(BaseModel):
    label: str
    impact_percent: float  # e.g. -12.5 means this factor reduced value by 12.5%
    description: str


class InstantValueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None  # populated only if saved (authenticated user)
    make: str
    model: str
    year: int
    mileage: int
    condition: VehicleCondition
    estimated_value: float
    value_range_low: float
    value_range_high: float
    confidence_score: float = Field(..., ge=0, le=1)
    factors: list[ValueFactor]
    generated_at: datetime
    saved: bool = False


class InstantValueHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    make: str
    model: str
    year: int
    estimated_value: float
    created_at: datetime
