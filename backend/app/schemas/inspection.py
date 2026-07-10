from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class InspectionBase(BaseModel):
    inspection_date: datetime
    inspector_name: str
    inspector_company: Optional[str] = None
    exterior_condition: str = "good"
    interior_condition: str = "good"
    mechanical_condition: str = "good"
    tire_condition: str = "good"
    mileage: float
    notes: Optional[str] = None
    photos: List[str] = []


class InspectionCreate(InspectionBase):
    pass


class InspectionUpdate(BaseModel):
    inspection_date: Optional[datetime] = None
    exterior_condition: Optional[str] = None
    interior_condition: Optional[str] = None
    mechanical_condition: Optional[str] = None
    tire_condition: Optional[str] = None
    mileage: Optional[float] = None
    notes: Optional[str] = None
    photos: Optional[List[str]] = None


class InspectionResponse(InspectionBase):
    id: str
    vehicle_id: str
    inspector_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class InspectionReport(InspectionResponse):
    vehicle: Optional[dict] = None
    overall_rating: Optional[str] = None
    recommendations: Optional[List[str]] = None
