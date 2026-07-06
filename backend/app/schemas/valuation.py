"""
Valuation Schemas - NO circular imports
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class PropertyType(str, Enum):
    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTI_FAMILY = "multi_family"
    COMMERCIAL = "commercial"
    VACANT_LAND = "vacant_land"


class PropertyCondition(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    NEEDS_RENOVATION = "needs_renovation"


class ValuationMethod(str, Enum):
    COMPARABLE = "comparable"
    INCOME = "income"
    COST = "cost"
    AUTOMATED = "automated"
    HYBRID = "hybrid"


class PropertyAddress(BaseModel):
    street: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=50)
    zip_code: str = Field(..., min_length=5, max_length=10)
    country: str = Field(default="USA", max_length=50)


class PropertyFeatures(BaseModel):
    bedrooms: Optional[int] = Field(None, ge=0, le=20)
    bathrooms: Optional[float] = Field(None, ge=0, le=20)
    square_feet: Optional[int] = Field(None, ge=0, le=1000000)
    lot_size_acres: Optional[float] = Field(None, ge=0, le=10000)
    year_built: Optional[int] = Field(None, ge=1800, le=datetime.now().year)
    garage_spaces: Optional[int] = Field(0, ge=0, le=10)
    pool: bool = False
    fireplace: bool = False
    basement: bool = False
    stories: Optional[int] = Field(1, ge=1, le=10)
    heating_type: Optional[str] = None
    cooling_type: Optional[str] = None
    waterfront: bool = False
    view: bool = False
    has_home_office: bool = False
    has_gym: bool = False


class ValuationRequest(BaseModel):
    property_id: Optional[str] = None
    address: PropertyAddress
    property_type: PropertyType
    features: PropertyFeatures
    condition: PropertyCondition = PropertyCondition.GOOD
    valuation_method: ValuationMethod = ValuationMethod.AUTOMATED
    include_comparables: bool = True
    include_trends: bool = True
    include_forecast: bool = False
    user_id: Optional[str] = None


class InstantValueRequest(BaseModel):
    property_id: Optional[str] = None
    address: PropertyAddress
    property_type: PropertyType
    features: PropertyFeatures
    condition: PropertyCondition = PropertyCondition.GOOD
    recent_sales_data: Optional[List[Dict[str, Any]]] = None
    market_trends: Optional[Dict[str, Any]] = None
    zpid: Optional[str] = None
    use_cache: bool = True
    user_id: Optional[str] = None


class ComparableProperty(BaseModel):
    address: str
    sale_price: float
    sale_date: date
    distance_miles: float
    square_feet: int
    bedrooms: int
    bathrooms: float
    condition: str
    adjusted_price: Optional[float] = None
    adjustment_factors: Optional[Dict[str, float]] = None


class MarketTrends(BaseModel):
    median_price: float
    price_per_sqft: float
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
    growth_rate: float


class ValuationResponse(BaseModel):
    property_id: Optional[str] = None
    estimated_value: float
    estimated_value_range_low: float
    estimated_value_range_high: float
    confidence_score: float
    valuation_method: ValuationMethod
    valuation_date: datetime = Field(default_factory=datetime.now)
    comparables: Optional[List[ComparableProperty]] = None
    market_trends: Optional[MarketTrends] = None
    forecast: Optional[List[ValuationForecast]] = None
    factors_influencing: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    data_source: Optional[str] = None
    computation_time_ms: Optional[int] = None
    cache_hit: bool = False


class InstantValueResponse(BaseModel):
    property_id: Optional[str] = None
    instant_value: float
    value_range: Dict[str, float]
    confidence_level: float
    estimated_at: datetime = Field(default_factory=datetime.now)
    price_per_sqft: Optional[float] = None
    vs_zip_median: Optional[float] = None
    vs_city_median: Optional[float] = None
    market_trend: Optional[str] = None
    days_on_market: Optional[int] = None
    supply_demand_ratio: Optional[float] = None
    data_source: str = "Automated Valuation Model"
    cache_hit: bool = False
    last_sale_price: Optional[float] = None
    last_sale_date: Optional[date] = None
