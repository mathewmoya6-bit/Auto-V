from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ==========================================================
# CREATE / UPDATE SCHEMAS
# ==========================================================

class AssessmentCreate(BaseModel):
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


class AssessmentUpdate(BaseModel):
    condition: Optional[str] = None
    mileage: Optional[int] = None
    price: Optional[float] = None
    location: Optional[str] = None
    service_history: Optional[bool] = None


# ==========================================================
# COMMON OBJECTS
# ==========================================================

class AssessmentFactor(BaseModel):
    category: str
    score: int
    max_score: int
    status: str
    icon: str
    description: str


class ConditionAssessment(BaseModel):
    overall_rating: str
    score: int
    max_score: int
    percentage: int
    color: str
    emoji: str
    details: List[AssessmentFactor]


class DepreciationForecastItem(BaseModel):
    year: str
    year_number: int
    projected_value: float
    depreciation: float
    percentage: float
    status: str


class InvestmentRecommendation(BaseModel):
    rating: str
    color: str
    emoji: str
    score: int
    max_score: int
    recommendations: List[Dict[str, Any]]


# ==========================================================
# RESPONSE
# ==========================================================

class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assessment_id: str
    market_value: float
    maintenance_cost: float
    generated_at: str

    condition_assessment: ConditionAssessment
    depreciation_forecast: List[DepreciationForecastItem]
    investment_recommendation: InvestmentRecommendation

    user_id: Optional[str] = None
    vehicle_details: Optional[Dict[str, Any]] = None


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
# BULK
# ==========================================================

class BulkAssessmentRequest(BaseModel):
    vehicles: List[Dict[str, Any]]


class BulkAssessmentResponse(BaseModel):
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]
    user_id: Optional[str] = None
    calculated_at: str


# ==========================================================
# COMPARISON
# ==========================================================

class AssessmentComparisonRequest(BaseModel):
    vehicles: List[Dict[str, Any]]


class AssessmentComparisonResponse(BaseModel):
    assessments: List[Dict[str, Any]]
    comparison: Dict[str, Any]
    user_id: Optional[str] = None
    calculated_at: str
