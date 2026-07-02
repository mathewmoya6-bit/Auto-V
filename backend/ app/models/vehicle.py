# app/models/vehicle.py
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

# ─── Vehicle Base ──────────────────────────────────────────────────

class VehicleBase(BaseModel):
    """Base vehicle model with common fields"""
    registration_number: str = Field(..., min_length=3, max_length=15)
    vin: Optional[str] = Field(None, min_length=17, max_length=17)
    make: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=1900, le=datetime.utcnow().year + 1)
    body_type: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=30)
    odometer: Optional[int] = Field(None, ge=0)
    engine_cc: Optional[int] = Field(None, ge=0)
    transmission: Optional[str] = Field(None, max_length=30)
    fuel_type: Optional[str] = Field(None, max_length=20)
    condition: Optional[str] = Field(None, regex="^(Excellent|Good|Fair|Poor)$")
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    images: Optional[List[str]] = []
    documents: Optional[Dict[str, str]] = {}  # document_type -> url
    
    @validator('registration_number')
    def validate_registration(cls, v):
        """Validate Kenyan vehicle registration format"""
        if not v:
            raise ValueError('Registration number is required')
        
        # Remove spaces and convert to uppercase
        v = v.upper().replace(' ', '')
        
        # Kenyan registration formats:
        # KCA 123A, KCA 1234A, KCA 123AB, etc.
        # Also handle newer formats
        pattern = r'^[A-Z]{3}\s?\d{3}[A-Z]{1,2}$|^[A-Z]{3}\s?\d{4}[A-Z]{1,2}$'
        
        # Basic validation - check length and structure
        if len(v) < 6 or len(v) > 10:
            raise ValueError('Invalid registration number format')
        
        # Must have at least 3 letters followed by numbers and letters
        if not re.match(r'^[A-Z]{3,4}[0-9]{3,4}[A-Z]{0,2}$', v):
            raise ValueError('Invalid registration number format')
        
        return v
    
    @validator('vin', always=True)
    def validate_vin(cls, v):
        """Validate VIN number"""
        if v is None:
            return v
        
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
    
    @validator('odometer')
    def validate_odometer(cls, v):
        if v is not None and v < 0:
            raise ValueError('Odometer cannot be negative')
        if v is not None and v > 1000000:
            raise ValueError('Odometer seems too high (max 1,000,000 km)')
        return v
    
    @validator('engine_cc')
    def validate_engine_cc(cls, v):
        if v is not None and v < 0:
            raise ValueError('Engine capacity cannot be negative')
        if v is not None and v > 10000:
            raise ValueError('Engine capacity seems too high (max 10,000 cc)')
        return v

# ─── Vehicle Create ──────────────────────────────────────────────────

class VehicleCreate(VehicleBase):
    """Model for creating a new vehicle"""
    user_id: Optional[str] = None  # Will be set from auth
    accident_history: Optional[str] = Field(None, regex="^(None|Minor|Moderate|Major)$")
    service_history: Optional[str] = Field(None, regex="^(Full|Partial|None)$")
    owners: Optional[int] = Field(None, ge=0)
    usage: Optional[str] = Field(None, regex="^(Personal|Commercial|Fleet|Rental)$")
    import_status: Optional[str] = Field(None, regex="^(Local|Imported|New Import)$")
    warranty: Optional[str] = Field(None, regex="^(Active|Expired|None)$")
    modifications: Optional[str] = Field(None, regex="^(None|Minor|Major|Extensive)$")
    
    # Inspection data
    inspection_data: Optional[Dict[str, Any]] = {}
    
    # Valuation data
    valuation_data: Optional[Dict[str, Any]] = {}

# ─── Vehicle Update ──────────────────────────────────────────────────

class VehicleUpdate(BaseModel):
    """Model for updating a vehicle"""
    registration_number: Optional[str] = Field(None, min_length=3, max_length=15)
    vin: Optional[str] = Field(None, min_length=17, max_length=17)
    make: Optional[str] = Field(None, min_length=1, max_length=50)
    model: Optional[str] = Field(None, min_length=1, max_length=50)
    year: Optional[int] = Field(None, ge=1900, le=datetime.utcnow().year + 1)
    body_type: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=30)
    odometer: Optional[int] = Field(None, ge=0)
    engine_cc: Optional[int] = Field(None, ge=0)
    transmission: Optional[str] = Field(None, max_length=30)
    fuel_type: Optional[str] = Field(None, max_length=20)
    condition: Optional[str] = Field(None, regex="^(Excellent|Good|Fair|Poor)$")
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    images: Optional[List[str]] = None
    documents: Optional[Dict[str, str]] = None
    status: Optional[str] = Field(None, regex="^(pending|active|sold|archived|verified)$")
    accident_history: Optional[str] = Field(None, regex="^(None|Minor|Moderate|Major)$")
    service_history: Optional[str] = Field(None, regex="^(Full|Partial|None)$")
    owners: Optional[int] = Field(None, ge=0)
    usage: Optional[str] = Field(None, regex="^(Personal|Commercial|Fleet|Rental)$")
    import_status: Optional[str] = Field(None, regex="^(Local|Imported|New Import)$")
    warranty: Optional[str] = Field(None, regex="^(Active|Expired|None)$")
    modifications: Optional[str] = Field(None, regex="^(None|Minor|Major|Extensive)$")
    inspection_data: Optional[Dict[str, Any]] = None
    valuation_data: Optional[Dict[str, Any]] = None

# ─── Vehicle Response ──────────────────────────────────────────────────

class VehicleResponse(VehicleBase):
    """Response model for vehicle data"""
    id: str
    user_id: str
    status: str
    accident_history: Optional[str] = None
    service_history: Optional[str] = None
    owners: Optional[int] = None
    usage: Optional[str] = None
    import_status: Optional[str] = None
    warranty: Optional[str] = None
    modifications: Optional[str] = None
    inspection_data: Optional[Dict[str, Any]] = None
    valuation_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

# ─── Vehicle List Response ──────────────────────────────────────────

class VehicleListResponse(BaseModel):
    """Response model for vehicle list"""
    total: int
    vehicles: List[VehicleResponse]
    limit: int
    offset: int

# ─── Vehicle Search ──────────────────────────────────────────────────

class VehicleSearchParams(BaseModel):
    """Search parameters for vehicles"""
    make: Optional[str] = None
    model: Optional[str] = None
    year_min: Optional[int] = Field(None, ge=1900)
    year_max: Optional[int] = Field(None, ge=1900)
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    odometer_min: Optional[int] = Field(None, ge=0)
    odometer_max: Optional[int] = Field(None, ge=0)
    condition: Optional[str] = Field(None, regex="^(Excellent|Good|Fair|Poor)$")
    location: Optional[str] = None
    status: Optional[str] = Field(None, regex="^(pending|active|sold|archived|verified)$")
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    sort_by: Optional[str] = Field(None, regex="^(created_at|price|year|mileage|updated_at)$")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    
    @root_validator
    def validate_year_range(cls, values):
        year_min = values.get('year_min')
        year_max = values.get('year_max')
        if year_min and year_max and year_min > year_max:
            raise ValueError('year_min cannot be greater than year_max')
        return values
    
    @root_validator
    def validate_price_range(cls, values):
        price_min = values.get('price_min')
        price_max = values.get('price_max')
        if price_min and price_max and price_min > price_max:
            raise ValueError('price_min cannot be greater than price_max')
        return values

# ─── Vehicle Valuation ──────────────────────────────────────────────────

class VehicleValuationRequest(BaseModel):
    """Request model for vehicle valuation"""
    vehicle_id: Optional[str] = None
    registration_number: Optional[str] = None
    make: str
    model: str
    year: int
    odometer: Optional[int] = None
    condition: Optional[str] = Field(None, regex="^(Excellent|Good|Fair|Poor)$")
    purpose: str = Field(..., regex="^(Market Value|Insurance Value|Trade-In Value|Forced Sale Value)$")
    methodology: Optional[str] = Field("Market Comparison", regex="^(Market Comparison|Cost Approach|Income Approach|Hybrid)$")
    region: Optional[str] = "National"
    inspection_data: Optional[Dict[str, Any]] = None
    history_data: Optional[Dict[str, Any]] = None

class VehicleValuationResponse(BaseModel):
    """Response model for vehicle valuation"""
    valuation_id: str
    market_value: float
    insurance_value: float
    trade_in_value: Optional[float] = None
    forced_sale_value: Optional[float] = None
    confidence_score: int = Field(..., ge=0, le=100)
    condition_score: Optional[float] = None
    risk_score: Optional[int] = Field(None, ge=0, le=100)
    comparables: Optional[List[Dict[str, Any]]] = None
    factors_used: Optional[Dict[str, Any]] = None
    methodology: str
    region: str
    purpose: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

# ─── Vehicle History ──────────────────────────────────────────────────

class VehicleHistory(BaseModel):
    """Vehicle history record"""
    id: str
    vehicle_id: str
    event_type: str = Field(..., regex="^(valuation|inspection|certificate|sale|service|accident|ownership)$")
    description: str
    details: Dict[str, Any] = {}
    occurred_at: datetime
    created_at: datetime

class VehicleHistoryResponse(BaseModel):
    """Response model for vehicle history"""
    history: List[VehicleHistory]
    total: int
    limit: int
    offset: int

# ─── Vehicle Document ──────────────────────────────────────────────────

class VehicleDocument(BaseModel):
    """Vehicle document model"""
    id: Optional[str] = None
    vehicle_id: str
    document_type: str = Field(..., regex="^(logbook|id|kra|insurance|service|inspection|valuation|certificate)$")
    document_name: str
    document_url: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    status: str = Field("pending", regex="^(pending|verified|rejected)$")
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class VehicleDocumentUpload(BaseModel):
    """Model for uploading vehicle documents"""
    vehicle_id: str
    document_type: str = Field(..., regex="^(logbook|id|kra|insurance|service|inspection|valuation|certificate)$")
    file_url: str  # URL after upload

# ─── Vehicle Image ──────────────────────────────────────────────────

class VehicleImage(BaseModel):
    """Vehicle image model"""
    id: Optional[str] = None
    vehicle_id: str
    url: str
    caption: Optional[str] = None
    order: int = 0
    is_primary: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True

# ─── Bulk Operations ──────────────────────────────────────────────────

class VehicleBulkCreate(BaseModel):
    """Model for bulk vehicle creation"""
    vehicles: List[VehicleCreate]
    skip_duplicates: bool = True

class VehicleBulkResponse(BaseModel):
    """Response for bulk vehicle operations"""
    total: int
    created: int
    skipped: int
    errors: List[Dict[str, Any]] = []

# ─── Vehicle Makes and Models ──────────────────────────────────────────────────

class VehicleMakeModel(BaseModel):
    """Vehicle make and model lookup"""
    make: str
    models: List[str]

class VehicleMakesResponse(BaseModel):
    """Response for vehicle makes and models"""
    makes: List[VehicleMakeModel]

# ─── Validation Helpers ──────────────────────────────────────────────────

def validate_kenyan_registration(reg: str) -> bool:
    """
    Validate Kenyan vehicle registration number.
    Formats: KCA 123A, KCA 1234A, KCA 123AB, etc.
    """
    if not reg:
        return False
    # Remove spaces and convert to uppercase
    reg = reg.upper().replace(' ', '')
    # Check pattern
    pattern = r'^[A-Z]{3}\d{3}[A-Z]{1,2}$|^[A-Z]{3}\d{4}[A-Z]{1,2}$'
    return bool(re.match(pattern, reg))

def normalize_registration(reg: str) -> str:
    """Normalize Kenyan registration number to KCA 123A format"""
    if not reg:
        return reg
    reg = reg.upper().replace(' ', '')
    # Insert space after first 3 characters
    if len(reg) >= 3:
        reg = reg[:3] + ' ' + reg[3:]
    return reg

def validate_vin(vin: str) -> bool:
    """Validate VIN number"""
    if not vin:
        return False
    vin = vin.upper().replace(' ', '').replace('-', '')
    if len(vin) != 17:
        return False
    invalid_chars = ['I', 'O', 'Q']
    for char in invalid_chars:
        if char in vin:
            return False
    return True
