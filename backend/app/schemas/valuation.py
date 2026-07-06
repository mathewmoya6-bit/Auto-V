"""
Valuation Schemas
Pydantic models for property valuation requests and responses
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

    @validator('zip_code')
    def validate_zip(cls, v):
        if not v.replace('-', '').isdigit():
            raise ValueError('Zip code must contain only digits and hyphens')
        return v


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
    """Request model for property valuation"""
    property_id: Optional[str] = Field(None, description="Existing property ID if available")
    address: PropertyAddress
    property_type: PropertyType
    features: PropertyFeatures
    condition: PropertyCondition = PropertyCondition.GOOD
    valuation_method: ValuationMethod = ValuationMethod.AUTOMATED
    include_comparables: bool = Field(True, description="Include comparable properties in response")
    include_trends: bool = Field(True, description="Include market trend analysis")
    include_forecast: bool = Field(False, description="Include 12-month value forecast")
    user_id: Optional[str] = None
    
    @validator('features')
    def validate_features(cls, v, values):
        """Ensure at least square_feet or lot_size is provided"""
        if not v.square_feet and not v.lot_size_acres:
            raise ValueError('Either square_feet or lot_size_acres must be provided')
        return v


class InstantValueRequest(BaseModel):
    """Request model for instant property value estimation"""
    property_id: Optional[str] = Field(None, description="Existing property ID if available")
    address: PropertyAddress
    property_type: PropertyType
    features: PropertyFeatures
    condition: PropertyCondition = PropertyCondition.GOOD
    recent_sales_data: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Recent comparable sales in the area"
    )
    market_trends: Optional[Dict[str, Any]] = Field(
        None,
        description="Market trend data for the area"
    )
    zpid: Optional[str] = Field(None, description="Zillow Property ID if available")
    use_cache: bool = Field(True, description="Use cached value if available")
    user_id: Optional[str] = None


class ComparableProperty(BaseModel):
    """Model for comparable property data"""
    address: str
    sale_price: float = Field(..., ge=0)
    sale_date: date
    distance_miles: float = Field(..., ge=0)
    square_feet: int = Field(..., ge=0)
    bedrooms: int = Field(..., ge=0)
    bathrooms: float = Field(..., ge=0)
    condition: str
    adjusted_price: Optional[float] = Field(None, ge=0)
    adjustment_factors: Optional[Dict[str, float]] = None


class MarketTrends(BaseModel):
    """Market trends data"""
    median_price: float = Field(..., ge=0)
    price_per_sqft: float = Field(..., ge=0)
    year_over_year_change: float
    month_over_month_change: float
    days_on_market_avg: int = Field(..., ge=0)
    inventory_count: int = Field(..., ge=0)
    market_health_score: float = Field(..., ge=0, le=100)
    trend_direction: str


class ValuationForecast(BaseModel):
    """12-month value forecast"""
    forecast_date: date
    predicted_value: float = Field(..., ge=0)
    confidence_lower: float = Field(..., ge=0)
    confidence_upper: float = Field(..., ge=0)
    growth_rate: float


class ValuationResponse(BaseModel):
    """Complete valuation response model"""
    property_id: Optional[str] = None
    estimated_value: float = Field(..., ge=0)
    estimated_value_range_low: float = Field(..., ge=0)
    estimated_value_range_high: float = Field(..., ge=0)
    confidence_score: float = Field(..., ge=0, le=100)
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
    """Response model for instant value estimation"""
    property_id: Optional[str] = None
    instant_value: float = Field(..., ge=0)
    value_range: Dict[str, float]
    confidence_level: float = Field(..., ge=0, le=100)
    estimated_at: datetime = Field(default_factory=datetime.now)
    price_per_sqft: Optional[float] = Field(None, ge=0)
    vs_zip_median: Optional[float] = None
    vs_city_median: Optional[float] = None
    market_trend: Optional[str] = None
    days_on_market: Optional[int] = None
    supply_demand_ratio: Optional[float] = None
    data_source: str = "Automated Valuation Model"
    cache_hit: bool = False
    last_sale_price: Optional[float] = None
    last_sale_date: Optional[date] = None
