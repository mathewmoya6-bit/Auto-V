from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class ValuationCreate(BaseModel):
    make: str
    model: str
    year: int
    engine_capacity: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    body_color: Optional[str] = None
    mileage: int
    condition: str
    accident_history: str
    location: str
    previous_owners: int = 0
    usage_type: str = "Personal"
    phone: str


class ValuationUpdate(BaseModel):
    market_value: Optional[float] = None
    confidence_score: Optional[int] = None
    certificate_number: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ValuationResponse(BaseModel):
    id: str
    user_id: str
    make: str
    model: str
    year: int
    engine_capacity: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    body_color: Optional[str] = None
    mileage: int
    condition: str
    accident_history: str
    location: str
    previous_owners: int
    usage_type: str
    phone: str
    market_value: Optional[float] = None
    confidence_score: Optional[int] = None
    certificate_number: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class InstantValuationRequest(BaseModel):
    user_id: Optional[str] = None
    vehicle: Dict[str, Any]
    phone: str
    valuation_id: Optional[str] = None


class InstantValuationResponse(BaseModel):
    market_value: float
    range_low: float
    range_high: float
    confidence_score: int
    certificate_number: str
    factors: Dict[str, Any]
    valuation_id: Optional[str] = None
    created_at: str


# ─── Assessment Schemas ────────────────────────────────────────────

class AssessmentFactor(BaseModel):
    category: str
    score: int
    status: str


class ConditionAssessment(BaseModel):
    overall_rating: str
    score: int
    color: str
    details: List[AssessmentFactor]


class DepreciationForecastItem(BaseModel):
    year: str
    projected_value: float
    depreciation: float
    percentage: float


class InvestmentRecommendation(BaseModel):
    rating: str
    color: str
    score: int
    recommendations: List[str]


class VehicleAssessmentRequest(BaseModel):
    vehicle: Dict[str, Any]
    price: Optional[float] = None
    valuation_id: Optional[str] = None


class VehicleAssessmentResponse(BaseModel):
    market_value: float
    condition_assessment: ConditionAssessment
    maintenance_cost: float
    depreciation_forecast: List[DepreciationForecastItem]
    investment_recommendation: InvestmentRecommendation
    valuation_id: Optional[str] = None
    generated_at: str
