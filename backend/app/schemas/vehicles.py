from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VehicleBase(BaseModel):
    make: str
    model: str
    year: int
    registration: str
    category_id: int
    vin: Optional[str] = None
    color: Optional[str] = None
    engine_size: Optional[float] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    condition: str = "good"


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    registration: Optional[str] = None
    category_id: Optional[int] = None
    vin: Optional[str] = None
    color: Optional[str] = None
    engine_size: Optional[float] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    condition: Optional[str] = None
    status: Optional[str] = None


class VehicleResponse(VehicleBase):
    id: str
    user_id: str
    current_mileage: float = 0
    status: str = "active"
    created_at: datetime
    updated_at: Optional[datetime] = None


class VehicleDetailResponse(VehicleResponse):
    category: Optional[dict] = None
    last_inspection: Optional[dict] = None
    valuation: Optional[dict] = None
