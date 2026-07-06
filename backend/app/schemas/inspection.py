"""
Inspection Schemas - NO circular imports
"""

from pydantic import BaseModel, Field, EmailStr
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
    item_name: str
    category: str
    status: str
    severity: Optional[InspectionSeverity] = None
    description: str
    recommendation: Optional[str] = None
    estimated_cost: Optional[float] = None
    is_urgent: bool = False
    photos: Optional[List[str]] = None
    notes: Optional[str] = None


class InspectionPhoto(BaseModel):
    url: str
    caption: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    location: Optional[str] = None


class InspectionRequest(BaseModel):
    property_id: str
    inspection_type: InspectionType
    scheduled_date: date
    scheduled_time: str
    duration_hours: Optional[float] = 2.0
    inspector_name: str
    inspector_company: Optional[str] = None
    inspector_license: Optional[str] = None
    inspector_phone: Optional[str] = None
    inspector_email: Optional[EmailStr] = None
    client_name: str
    client_email: EmailStr
    client_phone: str
    client_relationship: Optional[str] = None
    additional_instructions: Optional[str] = None
    areas_to_inspect: Optional[List[str]] = None
    priority_areas: Optional[List[str]] = None
    excluded_areas: Optional[List[str]] = None
    access_instructions: Optional[str] = None
    key_location: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_phone: Optional[str] = None
    include_photos: bool = True
    include_thermal: bool = False
    include_environmental: bool = False
    emergency_contact: Optional[str] = None
    special_equipment_needed: Optional[List[str]] = None


class InspectionReport(BaseModel):
    inspection_id: str
    property_id: str
    report_number: str
    inspection_date: date
    report_date: datetime = Field(default_factory=datetime.now)
    inspection_type: InspectionType
    inspector_name: str
    inspector_license: Optional[str] = None
    inspector_company: Optional[str] = None
    property_address: Dict[str, str]
    property_age: Optional[int] = None
    property_condition_rating: Optional[float] = None
    summary: str
    items: List[InspectionItem]
    total_issues: int
    critical_issues: int
    major_issues: int
    moderate_issues: int
    minor_issues: int
    estimated_repair_cost_low: Optional[float] = None
    estimated_repair_cost_high: Optional[float] = None
    photos: Optional[List[InspectionPhoto]] = None
    attachments: Optional[List[str]] = None
    overall_recommendation: str
    urgent_actions: List[str]
    maintenance_tips: Optional[List[str]] = None
    status: InspectionStatus
    report_version: str = "1.0"
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
    cancellation_reason: Optional[str] = None
    reschedule_reason: Optional[str] = None


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
    estimated_duration: float


class InspectionChecklist(BaseModel):
    checklist_id: str
    inspection_type: InspectionType
    name: str
    description: str
    items: List[Dict[str, Any]]
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
