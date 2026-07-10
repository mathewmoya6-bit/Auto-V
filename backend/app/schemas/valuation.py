# app/schemas/valuation.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime


class ValuationRequest(BaseModel):
    """Request model for creating a valuation"""
    make: str
    model: str
    year: int
    mileage: int
    condition: str = "Good"
    accident_history: str = "None"
    location: str = "Other"
    previous_owners: int = 1
    usage_type: str = "Personal"
    fuel_type: str = "Petrol"
    transmission: str = "Manual"
    body_type: str = "Sedan"
    engine_capacity: int = 1500
    service_history: bool = False


class ValuationCreate(BaseModel):
    """Model for creating a valuation record"""
    vehicle_id: UUID
    mileage: int
    condition: str
    accident_history: str
    location: str
    previous_owners: int
    usage_type: str


class ValuationUpdate(BaseModel):
    """Model for updating a valuation"""
    market_value: Optional[float] = None
    confidence_score: Optional[int] = None
    certificate_number: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ValuationResponse(BaseModel):
    """Response model for valuation"""
    id: UUID
    user_id: UUID
    vehicle_id: UUID
    make: str
    model: str
    year: int
    mileage: int
    condition: str
    accident_history: str
    location: str
    previous_owners: int
    usage_type: str
    market_value: float
    confidence_score: int
    certificate_number: str
    status: str
    factors: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ValuationHistory(BaseModel):
    """Model for valuation history"""
    id: UUID
    vehicle_id: UUID
    market_value: float
    confidence_score: int
    created_at: datetime


class ValuationStats(BaseModel):
    """Statistics for valuations"""
    total_valuations: int
    average_value: float
    average_confidence: float
    highest_value: float
    lowest_value: float
    last_30_days: int


class InstantValueRequest(BaseModel):
    """Request for instant valuation"""
    type: str = "Car"
    make: str
    model: str
    year: int
    mileage: int
    condition: str = "Good"
    accident_history: str = "None"
    location: str = "Other"
    previous_owners: int = 1
    fuel_type: str = "Petrol"
    transmission: str = "Manual"
    body_type: str = "Sedan"
    engine_capacity: int = 1500
    service_history: bool = False


class InstantValueResponse(BaseModel):
    """Response for instant valuation"""
    market_value: float
    range_low: float
    range_high: float
    confidence_score: int
    certificate_number: str
    factors: Dict[str, Any]
    created_at: str


# __all__ export
__all__ = [
    "ValuationRequest",
    "ValuationCreate",
    "ValuationUpdate",
    "ValuationResponse",
    "ValuationHistory",
    "ValuationStats",
    "InstantValueRequest",
    "InstantValueResponse"
]
