from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class AssessmentFactor(BaseModel):
    """Individual assessment factor"""
    category: str
    score: int
    max_score: int
    status: str
    icon: str
    description: str


class ConditionAssessment(BaseModel):
    """Condition assessment results"""
    overall_rating: str
    score: int
    max_score: int
    percentage: int
    color: str
    emoji: str
    details: List[AssessmentFactor]


class DepreciationForecastItem(BaseModel):
    """Depreciation forecast for a single year"""
    year: str
    year_number: int
    projected_value: float
    depreciation: float
    percentage: float
    status: str


class InvestmentRecommendation(BaseModel):
    """Investment recommendation"""
    rating: str
    color: str
    emoji: str
    score: int
    max_score: int
    recommendations: List[Dict[str, Any]]


class VehicleAssessmentRequest(BaseModel):
    """Request model for vehicle assessment"""
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
    price: Optional[float] = None  # For investment recommendation
    usage_type: str = "Personal"


class VehicleAssessmentResponse(BaseModel):
    """Response model for vehicle assessment"""
    market_value: float
    condition_assessment: ConditionAssessment
    maintenance_cost: float
    depreciation_forecast: List[DepreciationForecastItem]
    investment_recommendation: InvestmentRecommendation
    assessment_id: str
    user_id: Optional[str] = None
    vehicle_details: Optional[Dict[str, Any]] = None
    generated_at: str


class AssessmentHistoryResponse(BaseModel):
    """Response model for assessment history"""
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
    """Statistics for vehicle assessments"""
    total_assessments: int
    average_value: float
    average_condition_score: float
    average_maintenance_cost: float
    highest_value: float
    lowest_value: float
    last_30_days: int
    investment_ratings: Dict[str, int]
    condition_ratings: Dict[str, int]


class BulkAssessmentRequest(BaseModel):
    """Request for bulk vehicle assessments"""
    vehicles: List[Dict[str, Any]]


class BulkAssessmentResponse(BaseModel):
    """Response for bulk vehicle assessments"""
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]
    user_id: Optional[str] = None
    calculated_at: str


class AssessmentComparisonRequest(BaseModel):
    """Request for comparing multiple vehicle assessments"""
    vehicles: List[Dict[str, Any]]


class AssessmentComparisonResponse(BaseModel):
    """Response for vehicle assessment comparison"""
    assessments: List[Dict[str, Any]]
    comparison: Dict[str, Any]
    user_id: Optional[str] = None
    calculated_at: str
