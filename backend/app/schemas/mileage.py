from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VehicleCategoryBase(BaseModel):
    name: str
    base_rate: float
    description: Optional[str] = None


class VehicleCategoryCreate(VehicleCategoryBase):
    pass


class VehicleCategoryResponse(VehicleCategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class MileageEntryBase(BaseModel):
    current_mileage: float
    recorded_date: datetime


class MileageEntryCreate(MileageEntryBase):
    pass


class MileageEntryResponse(MileageEntryBase):
    id: int
    vehicle_id: str
    previous_mileage: Optional[float] = None
    created_at: datetime
