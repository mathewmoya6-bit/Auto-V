from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class InstantValueRequest(BaseModel):
    """Request model for instant vehicle valuation"""
    type: str = "Car"  # Car, Bike, Tricycle
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
    body_color: Optional[str] = None
    usage_type: str = "Personal"


class InstantValueResponse(BaseModel):
    """Response model for instant vehicle valuation"""
    market_value: float
    range_low: float
    range_high: float
    confidence_score: int
    certificate_number: str
    factors: Dict[str, Any]
    vehicle_details: Dict[str, Any]
    user_id: Optional[str] = None
    request_id: str
    calculated_at: str


class InstantValueHistoryResponse(BaseModel):
    """Response model for instant valuation history"""
    id: UUID
    user_id: str
    make: str
    model: str
    year: int
    mileage: int
    condition: str
    location: str
    market_value: float
    confidence_score: int
    certificate_number: str
    factors: Dict[str, Any]
    vehicle_details: Dict[str, Any]
    created_at: datetime


class InstantValueStats(BaseModel):
    """Statistics for instant valuations"""
    total_valuations: int
    average_value: float
    average_confidence: float
    highest_value: float
    lowest_value: float
    last_30_days: int
    most_common_make: Optional[str]
    most_common_model: Optional[str]


class BulkInstantValueRequest(BaseModel):
    """Request for bulk instant valuation"""
    vehicles: List[Dict[str, Any]]


class BulkInstantValueResponse(BaseModel):
    """Response for bulk instant valuation"""
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]
    user_id: Optional[str] = None
    calculated_at: str
