# app/schemas/vehicle_assessment.py
"""
Pydantic schemas for the Vehicle Assessments module.

A Vehicle Assessment is a composite snapshot: it pulls the vehicle's latest
Inspection, latest Valuation, and Mileage trend together into one overall
score + recommendations. It does not replace those modules — it summarizes
them for a "how is this vehicle doing overall" view.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ConditionGrade(str, Enum):
    excellent = "A"
    good = "B"
    fair = "C"
    poor = "D"
    critical = "F"


class AssessmentCreate(BaseModel):
    notes: Optional[str] = Field(None, description="Optional context from the requester")
    include_inspection: bool = True
    include_valuation: bool = True
    include_mileage_trend: bool = True


class ComponentScore(BaseModel):
    category: str  # e.g. "Mechanical", "Body & Paint", "Mileage Consistency", "Market Value"
    score: float = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1)
    notes: Optional[str] = None


class ValuationSnapshot(BaseModel):
    valuation_id: Optional[UUID] = None
    estimated_value: Optional[float] = None
    valuation_date: Optional[datetime] = None


class InspectionSnapshot(BaseModel):
    inspection_id: Optional[UUID] = None
    inspection_date: Optional[datetime] = None
    summary: Optional[str] = None


class MileageTrendSnapshot(BaseModel):
    latest_mileage: Optional[int] = None
    average_monthly_km: Optional[float] = None
    trend: Optional[str] = None  # "normal", "high_usage", "low_usage", "inconsistent"


class VehicleAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    overall_score: float = Field(..., ge=0, le=100)
    condition_grade: ConditionGrade
    component_scores: list[ComponentScore]
    valuation_snapshot: Optional[ValuationSnapshot] = None
    inspection_snapshot: Optional[InspectionSnapshot] = None
    mileage_trend_snapshot: Optional[MileageTrendSnapshot] = None
    recommendations: list[str]
    notes: Optional[str] = None
    created_at: datetime


class VehicleAssessmentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    overall_score: float
    condition_grade: ConditionGrade
    created_at: datetime


class VehicleAssessmentReport(BaseModel):
    """A slightly more narrative, print/export-friendly version of the assessment."""

    assessment: VehicleAssessmentResponse
    headline: str
    generated_at: datetime
