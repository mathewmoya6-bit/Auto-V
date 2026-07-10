from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ValuationRequest(BaseModel):
    vehicle_id: Optional[str] = None
    category_id: int
    year: int
    mileage: float
    condition: str = "good"
    extras: List[str] = []


class ValuationResponse(BaseModel):
    vehicle_id: Optional[str] = None
    base_value: float
    adjusted_value: float
    final_value: float
    factors: dict
    calculated_at: str


class ValuationHistory(BaseModel):
    date: str
    mileage: float
    value: float
