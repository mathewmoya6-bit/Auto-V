from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ==========================================================
# Assessment Factor
# ==========================================================

class AssessmentFactor(BaseModel):
    category: str
    score: int
    max_score: int
    status: str
    icon: str
    description: str


# ==========================================================
# Condition Assessment
# ==========================================================

class ConditionAssessment(BaseModel):
    overall_rating: str
    score: int
    max_score: int
    percentage: int
    color: str
    emoji: str
    details: List[AssessmentFactor]


# ==========================================================
# Depreciation Forecast
# ==========================================================

class DepreciationForecastItem(BaseModel):
    year: str
    year_number: int
    projected_value: float
    depreciation: float
    percentage: float
    status: str


# ==========================================================
# Investment Recommendation
# ==========================================================

class InvestmentRecommendation(BaseModel):
    rating: str
    color: str
    emoji: str
    score: int
    max_score: int
    recommendations: List[Dict[str, Any]]


# ==========================================================
# Create Assessment
# ==========================================================

class AssessmentCreate(BaseModel):
    make: str
    model: str
    year: int
    mileage: int
    condition: str
    location: str


# ==========================================================
# Update Assessment
# ==========================================================

class AssessmentUpdate(BaseModel):
    mileage: Optional[int] = None
    condition: Optional[str] = None
    location: Optional[str] = None


# ==========================================================
# Vehicle Assessment Request
# ==========================================================

class VehicleAssessmentRequest(BaseModel):

    type: str = "Car"

    make: str
    model: str
    year: int
    mileage: int

    condition: str = "Good"
    accident_history: str = "None"
    location: str = "Other"

    previous_owners: int = 1
    fuel_type: str = "Petrol"
    transmission: str = "Manual"
    body_type: str = "Sedan"

    engine_capacity: int = 1500
    service_history: bool = False

    body_condition: Optional[str] = None
    interior_condition: Optional[str] = None
    mechanical_condition: Optional[str] = None

    tire_condition: Optional[str] = "Good"

    price: Optional[float] = None
    usage_type: str = "Personal"


# ==========================================================
# Vehicle Assessment Response
# ==========================================================

class VehicleAssessmentResponse(BaseModel):

    market_value: float

    condition_assessment: ConditionAssessment

    maintenance_cost: float

    depreciation_forecast: List[DepreciationForecastItem]

    investment_recommendation: InvestmentRecommendation

    assessment_id: str

    user_id: Optional[str] = None

    vehicle_details: Optional[Dict[str, Any]] = None

    generated_at: str


# ==========================================================
# History
# ==========================================================

class AssessmentHistoryResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    user_id: str

    make: str
    model: str

    year: int
    mileage: int

    condition: str
    location: str

    market_value: float

    condition_score: int
    condition_rating: str

    maintenance_cost: float

    investment_rating: str

    assessment_data: Dict[str, Any]

    created_at: datetime


# ==========================================================
# Stats
# ==========================================================

class AssessmentStats(BaseModel):

    total_assessments: int

    average_value: float

    average_condition_score: float

    average_maintenance_cost: float

    highest_value: float

    lowest_value: float

    last_30_days: int

    investment_ratings: Dict[str, int]

    condition_ratings: Dict[str, int]


# ==========================================================
# Bulk Assessment
# ==========================================================

class BulkAssessmentRequest(BaseModel):
    vehicles: List[Dict[str, Any]]


class BulkAssessmentResponse(BaseModel):
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]
    user_id: Optional[str] = None
    calculated_at: str


# ==========================================================
# Compare
# ==========================================================

class AssessmentComparisonRequest(BaseModel):
    vehicles: List[Dict[str, Any]]


class AssessmentComparisonResponse(BaseModel):
    assessments: List[Dict[str, Any]]
    comparison: Dict[str, Any]
    user_id: Optional[str] = None
    calculated_at: str
