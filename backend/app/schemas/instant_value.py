from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class InstantValueRequest(BaseModel):
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
    body_color: Optional[str] = None
    usage_type: str = "Personal"

    valuation_id: Optional[str] = None


class InstantValueResponse(BaseModel):
    market_value: float
    range_low: float
    range_high: float
    confidence_score: int
    certificate_number: str

    factors: Dict[str, Any]

    valuation_id: str
    created_at: str
