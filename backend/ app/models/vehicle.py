# app/models/vehicle.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class VehicleBase(BaseModel):
    vin: str = Field(..., min_length=17, max_length=17)
    make: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=1900, le=datetime.utcnow().year + 1)
    color: Optional[str] = Field(None, max_length=30)
    mileage: Optional[int] = Field(None, ge=0)
    engine_type: Optional[str] = Field(None, max_length=50)
    transmission: Optional[str] = Field(None, max_length=30)
    fuel_type: Optional[str] = Field(None, max_length=20)
    condition: str = Field(..., regex="^(excellent|good|fair|poor)$")
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    images: Optional[List[str]] = []
    
    @validator('vin')
    def validate_vin(cls, v):
        # Remove any spaces or special characters
        v = v.upper().replace(' ', '').replace('-', '')
        
        # Basic VIN validation (17 characters, no I, O, Q)
        if len(v) != 17:
            raise ValueError('VIN must be 17 characters')
        
        invalid_chars = ['I', 'O', 'Q']
        for char in invalid_chars:
            if char in v:
                raise ValueError(f'VIN cannot contain {char}')
        
        return v
    
    @validator('year')
    def validate_year(cls, v):
        current_year = datetime.utcnow().year
        if v < 1900 or v > current_year + 1:
            raise ValueError(f'Year must be between 1900 and {current_year + 1}')
        return v
    
    @validator('mileage')
    def validate_mileage(cls, v):
        if v is not None and v < 0:
            raise ValueError('Mileage cannot be negative')
        return v

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    make: Optional[str] = Field(None, min_length=1, max_length=50)
    model: Optional[str] = Field(None, min_length=1, max_length=50)
    year: Optional[int] = Field(None, ge=1900, le=datetime.utcnow().year + 1)
    color: Optional[str] = Field(None, max_length=30)
    mileage: Optional[int] = Field(None, ge=0)
    engine_type: Optional[str] = Field(None, max_length=50)
    transmission: Optional[str] = Field(None, max_length=30)
    fuel_type: Optional[str] = Field(None, max_length=20)
    condition: Optional[str] = Field(None, regex="^(excellent|good|fair|poor)$")
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    images: Optional[List[str]] = None
    status: Optional[str] = Field(None, regex="^(pending|active|sold|verified)$")

class VehicleResponse(VehicleBase):
    id: str
    user_id: str
    status: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class VehicleSearchParams(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    condition: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = "active"
    limit: int = 20
    offset: int = 0
