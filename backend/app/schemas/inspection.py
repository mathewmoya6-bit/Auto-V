"""
Inspection Schemas
Pydantic models for property inspection requests and responses
"""

from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class InspectionType(str, Enum):
    GENERAL = "general"
    STRUCTURAL = "structural"
    HVAC = "hvac"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    ROOF = "roof"
    PEST = "pest"
    MOLD = "mold"
    RADON = "radon"
    SEPTIC = "septic"
    POOL = "pool"
    COMPLETE = "complete"
    BUYER = "buyer"
    SELLER = "seller"
    PRE_LISTING = "pre_listing"
    INSURANCE = "insurance"


class InspectionStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    DELAYED = "delayed"
    REVIEW_NEEDED = "review_needed"
    REPORT_PENDING = "report_pending"
    REPORT_COMPLETED = "report_completed"


class InspectionSeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"
    SAFETY_HAZARD = "safety_hazard"


class InspectionItem(BaseModel):
    item_name: str = Field(..., description="Name of the item inspected")
    category: str = Field(..., description="Category (e.g., Structural, Electrical)")
    status: str = Field(..., description="Status: Pass, Fail, Warning, N/A")
    severity: Optional[InspectionSeverity] = None
    description: str = Field(..., description="Detailed description of findings")
    recommendation: Optional[str] = Field(None, description="Recommended action")
    estimated_cost: Optional[float] = Field(None, ge=0, description="Estimated repair cost")
    is_urgent: bool = Field(False, description="Requires immediate attention")
    photos: Optional[List[str]] = Field(None, description="Photo URLs")
    notes: Optional[str] = None


class InspectionPhoto(BaseModel):
    url: str
    caption: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    location: Optional[str] = None


class InspectionRequest(BaseModel):
    property_id: str = Field(..., description="ID of the property to inspect")
    inspection_type: InspectionType
    scheduled_date: date
    scheduled_time: str = Field(..., description="Time in 12-hour format: 09:00 AM")
    duration_hours: Optional[float] = Field(2.0, ge=0.5, le=8)
    inspector_name: str = Field(..., min_length=2, max_length=100)
    inspector_company: Optional[str] = Field(None, max_length=100)
    inspector_license: Optional[str] = Field(None, max_length=50)
    inspector_phone: Optional[str] = None
    inspector_email: Optional[EmailStr] = None
    client_name: str = Field(..., min_length=2, max_length=100)
    client_email: EmailStr
    client_phone: str = Field(..., min_length=10, max_length=15)
    client_relationship: Optional[str] = Field(None, description="Buyer, Seller, Owner, etc.")
    additional_instructions: Optional[str] = Field(None, max_length=500)
    areas_to_inspect: Optional[List[str]] = Field(None, description="Specific areas to focus on")
    priority_areas: Optional[List[str]] = Field(None, description="High priority areas")
    excluded_areas: Optional[List[str]] = Field(None, description="Areas to exclude")
    access_instructions: Optional[str] = Field(None, max_length=500)
    key_location: Optional[str] = Field(None, max_length=200)
    contact_person_name: Optional[str] = None
    contact_person_phone: Optional[str] = None
    include_photos: bool = Field(True, description="Include photos in report")
    include_thermal: bool = Field(False, description="Thermal imaging inspection")
    include_environmental: bool = Field(False, description="Environmental testing")
    emergency_contact: Optional[str] = None
    special_equipment_needed: Optional[List[str]] = None
    
    @validator('scheduled_time')
    def validate_time(cls, v):
        import re
        pattern = r'^(0?[1-9]|1[0-2]):[0-5][0-9]\s*(AM|PM)$'
        if not re.match(pattern, v.upper()):
            raise ValueError('Time must be in format: 09:00 AM')
        return v.upper()
    
    @validator('client_phone')
    def validate_phone(cls, v):
        clean = ''.join(filter(str.isdigit, v))
        if len(clean) < 10:
            raise ValueError('Phone number must have at least 10 digits')
        return v


class InspectionReport(BaseModel):
    inspection_id: str
    property_id: str
    report_number: str = Field(..., description="Unique report identifier")
    inspection_date: date
    report_date: datetime = Field(default_factory=datetime.now)
    inspection_type: InspectionType
    inspector_name: str
    inspector_license: Optional[str] = None
    inspector_company: Optional[str] = None
    property_address: Dict[str, str]
    property_age: Optional[int] = None
    property_condition_rating: Optional[float] = Field(None, ge=0, le=10)
    summary: str = Field(..., max_length=1000)
    items: List[InspectionItem] = Field(..., description="All inspection items")
    total_issues: int = Field(..., ge=0)
    critical_issues: int = Field(..., ge=0)
    major_issues: int = Field(..., ge=0)
    moderate_issues: int = Field(..., ge=0)
    minor_issues: int = Field(..., ge=0)
    estimated_repair_cost_low: Optional[float] = Field(None, ge=0)
    estimated_repair_cost_high: Optional[float] = Field(None, ge=0)
    photos: Optional[List[InspectionPhoto]] = None
    attachments: Optional[List[str]] = Field(None, description="Additional file URLs")
    overall_recommendation: str = Field(..., description="Overall recommendation")
    urgent_actions: List[str] = Field(..., description="Urgent actions needed")
    maintenance_tips: Optional[List[str]] = None
    status: InspectionStatus
    report_version: str = Field(default="1.0")
    generated_by: Optional[str] = None
    notes: Optional[str] = None


class InspectionUpdateRequest(BaseModel):
    inspection_id: str
    status: Optional[InspectionStatus] = None
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[str] = None
    inspector_name: Optional[str] = None
    inspector_company: Optional[str] = None
    inspector_license: Optional[str] = None
    additional_instructions: Optional[str] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = Field(None, max_length=500)
    reschedule_reason: Optional[str] = Field(None, max_length=500)
    
    @validator('scheduled_time')
    def validate_time(cls, v):
        if v is None:
            return v
        import re
        pattern = r'^(0?[1-9]|1[0-2]):[0-5][0-9]\s*(AM|PM)$'
        if not re.match(pattern, v.upper()):
            raise ValueError('Time must be in format: 09:00 AM')
        return v.upper()


class InspectionResponse(BaseModel):
    inspection_id: str
    property_id: str
    inspection_type: InspectionType
    status: InspectionStatus
    scheduled_date: date
    scheduled_time: str
    inspector_name: str
    inspector_company: Optional[str] = None
    client_name: str
    client_email: EmailStr
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    report_generated: bool = False
    report_url: Optional[str] = None
    can_cancel: bool = True
    can_reschedule: bool = True
    estimated_duration: float = Field(..., ge=0)


class InspectionChecklist(BaseModel):
    checklist_id: str
    inspection_type: InspectionType
    name: str
    description: str
    items: List[Dict[str, Any]]
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
