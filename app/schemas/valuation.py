# app/schemas/valuation.py
# =============================================================================
# AUTO-V API - Valuation Schemas
# =============================================================================
"""
Assumes a Supabase table `valuations` with columns matching
ValuationResponse below (vehicle_id, user_id, estimated_value,
estimated_value_range_low/high, confidence_score, method, factors,
created_at).
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ValuationRequest(BaseModel):
    vehicle_id: UUID
    base_price: float = Field(
        ..., gt=0, description="Original/reference price (KES) the depreciation model starts from"
    )
    condition_override: Optional[str] = Field(
        None,
        pattern="^(excellent|good|fair|poor|salvage)$",
        description="Overrides the vehicle's stored condition for this valuation only",
    )


class ValuationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    vehicle_id: UUID
    user_id: UUID
    estimated_value: float
    estimated_value_range_low: float
    estimated_value_range_high: float
    confidence_score: float
    method: str = "depreciation_model_v1"
    factors: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


ValuationCreate = ValuationRequest
InstantValuationRequest = ValuationRequest
InstantValuationResponse = ValuationResponse
