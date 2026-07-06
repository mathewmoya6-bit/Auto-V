"""
Instant Value Schemas - NO circular imports
"""

from pydantic import BaseModel, Field
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
    ZILLOW = "zillow"
    REDFIN = "redfin"
    REALTOR = "realtor"
    COUNTY = "county_records"
    MLS = "mls"
    INTERNAL = "internal_algorithm"
    HYBRID = "hybrid"


class InstantValueBaseRequest(BaseModel):
    property_id: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    property_type: PropertyType
    square_feet: Optional[int] = None
    lot_size_acres: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    year_built: Optional[int] = None
    condition: PropertyCondition = PropertyCondition.GOOD
    has_pool: bool = False
    has_garage: bool = False
    has_basement: bool = False
    has_fireplace: bool = False
    stories: Optional[int] = 1
    waterfront: bool = False
    view: bool = False
    data_sources: Optional[List[DataSource]] = [DataSource.HYBRID]
    use_cache: bool = True


class InstantValueLocationFactors(BaseModel):
    zip_code_median_value: Optional[float] = None
    city_median_value: Optional[float] = None
    county_median_value: Optional[float] = None
    neighborhood_rating: Optional[float] = None
    school_rating: Optional[float] = None
    crime_index: Optional[float] = None
    walkability_score: Optional[float] = None
    proximity_to_amenities: Optional[float] = None


class InstantValueRecentSale(BaseModel):
    sale_price: float
    sale_date: date
    address: str
    distance_miles: float
    square_feet: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    property_type: Optional[PropertyType] = None
    condition: Optional[PropertyCondition] = None


class InstantValueMarketData(BaseModel):
    median_days_on_market: Optional[int] = None
    inventory_count: Optional[int] = None
    price_trend_6month: Optional[float] = None
    price_trend_12month: Optional[float] = None
    sales_volume: Optional[int] = None
    supply_demand_score: Optional[float] = None
    market_condition: Optional[str] = None
    seasonality_factor: Optional[float] = None


class InstantValueDetails(BaseModel):
    base_value: float
    location_adjustment: Optional[float] = 0
    condition_adjustment: Optional[float] = 0
    features_adjustment: Optional[float] = 0
    market_adjustment: Optional[float] = 0
    final_value: float
    confidence_score: float
    adjustment_factors: Optional[Dict[str, float]] = None


class InstantValueComparison(BaseModel):
    vs_zip_median: Optional[float] = None
    vs_city_median: Optional[float] = None
    vs_county_median: Optional[float] = None
    vs_national_median: Optional[float] = None
    percentile_estimate: Optional[float] = None
    price_per_sqft_rank: Optional[str] = None


class InstantValueResponse(BaseModel):
    property_id: Optional[str] = None
    estimated_value: float
    value_range_low: float
    value_range_high: float
    confidence_score: float
    details: Optional[InstantValueDetails] = None
    comparable_sales: Optional[List[InstantValueRecentSale]] = None
    location_factors: Optional[InstantValueLocationFactors] = None
    market_data: Optional[InstantValueMarketData] = None
    comparison: Optional[InstantValueComparison] = None
    price_per_sqft: Optional[float] = None
    estimated_mortgage: Optional[float] = None
    estimated_taxes: Optional[float] = None
    valuation_date: datetime = Field(default_factory=datetime.now)
    data_source: List[DataSource]
    algorithm_version: str = "2.0"
    cache_hit: bool = False
    computation_time_ms: Optional[int] = None
    property_address: Dict[str, str]
    property_type: PropertyType
    square_feet: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None


class InstantValueBatchRequest(BaseModel):
    properties: List[InstantValueBaseRequest]
    include_details: bool = False
    max_parallel: int = 10


class InstantValueBatchResponse(BaseModel):
    results: List[InstantValueResponse]
    total_properties: int
    successful_valuations: int
    failed_valuations: int
    errors: Optional[List[Dict[str, str]]] = None
    total_computation_time_ms: Optional[int] = None


class InstantValueHistory(BaseModel):
    property_id: str
    valuations: List[Dict[str, Any]]
    price_trend: Optional[str] = None
    average_change_percent: Optional[float] = None
    last_updated: datetime = Field(default_factory=datetime.now)


class InstantValueAccuracyMetrics(BaseModel):
    prediction_error_mean: float
    prediction_error_median: float
    prediction_error_std: float
    mean_absolute_percentage_error: float
    r_squared: float
    sample_size: int
    confidence_interval_90_percent: Dict[str, float]
    last_calculation_date: datetime = Field(default_factory=datetime.now)
