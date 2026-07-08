"""
Valuation Schemas - NO circular imports
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class VehicleCondition(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    SALVAGE = "salvage"


class ValuationMethod(str, Enum):
    COMPARABLE = "comparable"
    MARKET_INDEX = "market_index"
    DEALER_QUOTE = "dealer_quote"
    AUTOMATED = "automated"
    HYBRID = "hybrid"


class VehicleFeatures(BaseModel):
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1900, le=datetime.now().year + 1)
    trim: Optional[str] = None
    mileage: int = Field(..., ge=0, le=2_000_000)
    engine_size: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    drive_type: Optional[str] = None
    color: Optional[str] = None
    number_of_previous_owners: Optional[int] = Field(None, ge=0, le=20)
    has_accident_history: bool = False
    is_imported: bool = False


class ValuationRequest(BaseModel):
    vehicle_id: Optional[str] = None
    vin: Optional[str] = Field(None, min_length=11, max_length=17)
    features: VehicleFeatures
    condition: VehicleCondition = VehicleCondition.GOOD
    valuation_method: ValuationMethod = ValuationMethod.AUTOMATED
    include_comparables: bool = True
    include_trends: bool = True
    include_forecast: bool = False
    user_id: Optional[str] = None


class InstantValueRequest(BaseModel):
    vehicle_id: Optional[str] = None
    vin: Optional[str] = Field(None, min_length=11, max_length=17)
    features: VehicleFeatures
    condition: VehicleCondition = VehicleCondition.GOOD
    recent_sales_data: Optional[List[Dict[str, Any]]] = None
    market_trends: Optional[Dict[str, Any]] = None
    use_cache: bool = True
    user_id: Optional[str] = None


class ComparableVehicle(BaseModel):
    listing_source: str
    sale_price: float
    sale_date: date
    mileage: int
    year: int
    condition: str
    location: Optional[str] = None
    adjusted_price: Optional[float] = None
    adjustment_factors: Optional[Dict[str, float]] = None


class MarketTrends(BaseModel):
    median_price: float
    price_per_km: Optional[float] = None
    year_over_year_change: float
    month_over_month_change: float
    days_on_market_avg: int
    inventory_count: int
    market_health_score: float
    trend_direction: str


class ValuationForecast(BaseModel):
    forecast_date: date
    predicted_value: float
    confidence_lower: float
    confidence_upper: float
    depreciation_rate: float


class ValuationResponse(BaseModel):
    vehicle_id: Optional[str] = None
    estimated_value: float
    estimated_value_range_low: float
    estimated_value_range_high: float
    confidence_score: float
    valuation_method: ValuationMethod
    valuation_date: datetime = Field(default_factory=datetime.now)
    comparables: Optional[List[ComparableVehicle]] = None
    market_trends: Optional[MarketTrends] = None
    forecast: Optional[List[ValuationForecast]] = None
    factors_influencing: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    data_source: Optional[str] = None
    computation_time_ms: Optional[int] = None
    cache_hit: bool = False


class InstantValueResponse(BaseModel):
    vehicle_id: Optional[str] = None
    instant_value: float
    value_range: Dict[str, float]
    confidence_level: float
    estimated_at: datetime = Field(default_factory=datetime.now)
    price_per_km: Optional[float] = None
    vs_model_median: Optional[float] = None
    vs_market_median: Optional[float] = None
    market_trend: Optional[str] = None
    days_on_market: Optional[int] = None
    supply_demand_ratio: Optional[float] = None
    data_source: str = "Automated Valuation Model"
    cache_hit: bool = False
    last_sale_price: Optional[float] = None
    last_sale_date: Optional[date] = None


# ── Names required by app/schemas/__init__.py ──────────────────────────

class ValuationUpdate(BaseModel):
    condition: Optional[VehicleCondition] = None
    valuation_method: Optional[ValuationMethod] = None
    include_comparables: Optional[bool] = None
    include_trends: Optional[bool] = None
    include_forecast: Optional[bool] = None


ValuationCreate = ValuationRequest
InstantValuationRequest = InstantValueRequest
InstantValuationResponse = InstantValueResponse
