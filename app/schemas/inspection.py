# app/schemas/inspection.py
# =============================================================================
# AUTO-V API - Inspection Schemas
# =============================================================================
"""
Assumes a Supabase table `inspections` with a JSONB `items` column
storing a list of InspectionItem records.
"""
from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InspectionType(str, Enum):
    GENERAL = "general"
    PRE_PURCHASE = "pre_purchase"
    INSURANCE = "insurance"
    ROADWORTHY = "roadworthy"
    ACCIDENT_DAMAGE = "accident_damage"


class InspectionStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ItemSeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    SAFETY_CRITICAL = "safety_critical"


class InspectionItemStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class InspectionItem(BaseModel):
    component: str = Field(..., description="e.g. 'brakes', 'engine', 'tyres'")
    status: InspectionItemStatus
    severity: Optional[ItemSeverity] = None
    notes: Optional[str] = None
    estimated_repair_cost: Optional[float] = None
    photos: Optional[List[str]] = None


class InspectionCreate(BaseModel):
    vehicle_id: UUID
    inspection_type: InspectionType = InspectionType.GENERAL
    scheduled_date: Optional[date] = None
    notes: Optional[str] = None


class InspectionUpdate(BaseModel):
    status: Optional[InspectionStatus] = None
    items: Optional[List[InspectionItem]] = None
    notes: Optional[str] = None
    scheduled_date: Optional[date] = None


class InspectionComplete(BaseModel):
    """Submitted by the inspector to finalize results."""
    items: List[InspectionItem]
    inspector_notes: Optional[str] = None


class InspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    user_id: UUID
    inspector_id: Optional[UUID] = None
    inspection_type: InspectionType
    status: InspectionStatus = InspectionStatus.SCHEDULED
    scheduled_date: Optional[date] = None
    items: List[InspectionItem] = Field(default_factory=list)
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    overall_condition: Optional[str] = None
    notes: Optional[str] = None
    inspector_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
