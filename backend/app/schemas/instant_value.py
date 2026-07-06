"""
Instant Value Schemas
Pydantic models for instant property value estimation
Fast, automated property valuations
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


class DataSource(str, Enum):
    """Data sources for instant valuation"""
    ZILLOW = "zillow"
    REDFIN = "redfin"
    REALTOR = "realtor"
    COUNTY = "county_records"
    MLS = "mls"
    INTERNAL = "internal_algorithm"
    HYBRID = "hybrid"


class InstantValueBaseRequest(BaseModel):
    """Base request for instant valuation"""
    property_id: Optional[str] = Field(None, description="Existing property ID")
    address_line1: str = Field(..., max_length=200)
    address_line2: Optional[str] = None
    city: str = Field(..., max_length=100)
    state: str = Field(..., min_length=2, max_length=50)
    zip_code: str = Field(..., min_length=5, max_length=10)
    property_type: PropertyType
    
    # Optional property details (provide at least one size metric)
    square_feet: Optional[int] = Field(None, ge=0)
    lot_size_acres: Optional[float] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=0, le=20)
    bathrooms: Optional[float] = Field(None, ge=0, le=20)
    year_built: Optional[int] = Field(None, ge=1800, le=datetime.now().year)
    condition: PropertyCondition = PropertyCondition.GOOD
    
    # Additional value factors
    has_pool: bool = False
    has_garage: bool = False
    has_basement: bool = False
    has_fireplace: bool = False
    stories: Optional[int] = Field(1, ge=1, le=10)
    waterfront: bool = False
    view: bool = False
    
    # Advanced options
    data_sources: Optional[List[DataSource]] = Field(
        default=[DataSource.HYBRID],
        description="Data sources to use"
    )
    use_cache: bool = Field(True, description="Use cached valuation if available")
    
    @validator('square_feet', 'lot_size_acres', pre=True, always=True)
    def validate_size(cls, v, values):
        """Ensure at least one size metric is provided"""
        if 'square_feet' in values and values.get('square_feet') is None:
            if 'lot_size_acres' in values and values.get('lot_size_acres') is None:
                raise ValueError('Either square_feet or lot_size_acres must be provided')
        return v


class InstantValueLocationFactors(BaseModel):
    """Location-based value factors"""
    zip_code_median_value: Optional[float] = Field(None, ge=0)
    city_median_value: Optional[float] = Field(None, ge=0)
    county_median_value: Optional[float] = Field(None, ge=0)
    neighborhood_rating: Optional[float] = Field(None, ge=0, le=10)
    school_rating: Optional[float] = Field(None, ge=0, le=10)
    crime_index: Optional[float] = Field(None, ge=0, le=100)
    walkability_score: Optional[float] = Field(None, ge=0, le=100)
    proximity_to_amenities: Optional[float] = Field(None, ge=0, le=10)


class InstantValueRecentSale(BaseModel):
    """Recent sale data for comparable analysis"""
    sale_price: float = Field(..., ge=0)
    sale_date: date
    address: str
    distance_miles: float = Field(..., ge=0)
    square_feet: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    property_type: Optional[PropertyType] = None
    condition: Optional[PropertyCondition] = None


class InstantValueMarketData(BaseModel):
    """Market data for instant valuation"""
    median_days_on_market: Optional[int] = None
    inventory_count: Optional[int] = Field(None, ge=0)
    price_trend_6month: Optional[float] = Field(None, description="6-month price trend percentage")
    price_trend_12month: Optional[float] = Field(None, description="12-month price trend percentage")
    sales_volume: Optional[int] = Field(None, ge=0)
    supply_demand_score: Optional[float] = Field(None, ge=0, le=100)
    market_condition: Optional[str] = None  # "seller", "buyer", "balanced"
    seasonality_factor: Optional[float] = Field(None, ge=0)


class InstantValueDetails(BaseModel):
    """Detailed valuation breakdown"""
    base_value: float = Field(..., ge=0, description="Base property value")
    location_adjustment: Optional[float] = Field(0, description="Adjustment for location")
    condition_adjustment: Optional[float] = Field(0, description="Adjustment for condition")
    features_adjustment: Optional[float] = Field(0, description="Adjustment for features")
    market_adjustment: Optional[float] = Field(0, description="Adjustment for market conditions")
    final_value: float = Field(..., ge=0)
    confidence_score: float = Field(..., ge=0, le=100)
    adjustment_factors: Optional[Dict[str, float]] = Field(
        None,
        description="All adjustment factors applied"
    )


class InstantValueComparison(BaseModel):
    """Comparison against market averages"""
    vs_zip_median: Optional[float] = Field(None, description="Ratio to zip median")
    vs_city_median: Optional[float] = Field(None, description="Ratio to city median")
    vs_county_median: Optional[float] = Field(None, description="Ratio to county median")
    vs_national_median: Optional[float] = Field(None, description="Ratio to national median")
    percentile_estimate: Optional[float] = Field(None, ge=0, le=100, description="Value percentile")
    price_per_sqft_rank: Optional[str] = Field(None, description="Low, Average, High")


class InstantValueResponse(BaseModel):
    """Complete instant value response"""
    property_id: Optional[str] = None
    estimated_value: float = Field(..., ge=0)
    value_range_low: float = Field(..., ge=0)
    value_range_high: float = Field(..., ge=0)
    confidence_score: float = Field(..., ge=0, le=100)
    
    # Valuation details
    details: Optional[InstantValueDetails] = None
    comparable_sales: Optional[List[InstantValueRecentSale]] = None
    location_factors: Optional[InstantValueLocationFactors] = None
    market_data: Optional[InstantValueMarketData] = None
    comparison: Optional[InstantValueComparison] = None
    
    # Pricing breakdown
    price_per_sqft: Optional[float] = Field(None, ge=0)
    estimated_mortgage: Optional[float] = Field(None, ge=0, description="Monthly mortgage estimate")
    estimated_taxes: Optional[float] = Field(None, ge=0, description="Annual property taxes")
    
    # Valuation metadata
    valuation_date: datetime = Field(default_factory=datetime.now)
    data_source: List[DataSource] = Field(..., description="Data sources used")
    algorithm_version: str = Field(default="2.0")
    cache_hit: bool = False
    computation_time_ms: Optional[int] = None
    
    # Property details (echoed from request)
    property_address: Dict[str, str]
    property_type: PropertyType
    square_feet: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "property_id": "prop_12345",
                "estimated_value": 475000,
                "value_range_low": 450000,
                "value_range_high": 500000,
                "confidence_score": 89.5,
                "details": {
                    "base_value": 460000,
                    "location_adjustment": 15000,
                    "condition_adjustment": 0,
                    "features_adjustment": 0,
                    "final_value": 475000,
                    "confidence_score": 89.5
                },
                "price_per_sqft": 250,
                "valuation_date": "2024-01-15T10:30:00",
                "data_source": ["hybrid"],
                "cache_hit": False,
                "property_address": {
                    "street": "123 Main St",
                    "city": "Springfield",
                    "state": "IL",
                    "zip_code": "62701"
                },
                "property_type": "single_family",
                "square_feet": 1900,
                "bedrooms": 3,
                "bathrooms": 2.5
            }
        }


class InstantValueBatchRequest(BaseModel):
    """Batch valuation request for multiple properties"""
    properties: List[InstantValueBaseRequest]
    include_details: bool = Field(False, description="Include detailed breakdowns")
    max_parallel: int = Field(10, ge=1, le=50, description="Maximum parallel valuations")


class InstantValueBatchResponse(BaseModel):
    """Batch valuation response"""
    results: List[InstantValueResponse]
    total_properties: int
    successful_valuations: int
    failed_valuations: int
    errors: Optional[List[Dict[str, str]]] = None
    total_computation_time_ms: Optional[int] = None


class InstantValueHistory(BaseModel):
    """Historical instant valuations for a property"""
    property_id: str
    valuations: List[Dict[str, Any]] = Field(..., description="List of historical valuations")
    price_trend: Optional[str] = Field(None, description="Up, Down, Stable")
    average_change_percent: Optional[float] = None
    last_updated: datetime = Field(default_factory=datetime.now)


class InstantValueAccuracyMetrics(BaseModel):
    """Accuracy metrics for instant valuation model"""
    prediction_error_mean: float
    prediction_error_median: float
    prediction_error_std: float
    mean_absolute_percentage_error: float
    r_squared: float
    sample_size: int
    confidence_interval_90_percent: Dict[str, float]
    last_calculation_date: datetime = Field(default_factory=datetime.now)
