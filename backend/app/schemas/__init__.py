"""
Schemas Package - Clean exports with no circular imports
"""

# Valuation schemas
from .valuation import (
    PropertyType,
    PropertyCondition,
    ValuationMethod,
    PropertyAddress,
    PropertyFeatures,
    ValuationRequest,
    InstantValueRequest,
    ComparableProperty,
    MarketTrends,
    ValuationForecast,
    ValuationResponse,
    InstantValueResponse
)

# Inspection schemas
from .inspection import (
    InspectionType,
    InspectionStatus,
    InspectionSeverity,
    InspectionItem,
    InspectionPhoto,
    InspectionRequest,
    InspectionReport,
    InspectionUpdateRequest,
    InspectionResponse,
    InspectionChecklist
)

# Instant Value schemas
from .instant_value import (
    InstantValueBaseRequest,
    InstantValueLocationFactors,
    InstantValueRecentSale,
    InstantValueMarketData,
    InstantValueDetails,
    InstantValueComparison,
    InstantValueResponse as InstantValueDetailedResponse,
    InstantValueBatchRequest,
    InstantValueBatchResponse,
    InstantValueHistory,
    InstantValueAccuracyMetrics,
    DataSource
)

# Mileage schemas
from .mileage import (
    CategoryOut,
    VariantOut,
    RouteOut,
    MileageClaimOut,
    MileageClaimCreate,
    MileageClaimUpdate,
    MileageClaimSummary,
    VehicleRateOut,
    MileageApprovalRequest
)

__all__ = [
    # Valuation
    'PropertyType',
    'PropertyCondition',
    'ValuationMethod',
    'PropertyAddress',
    'PropertyFeatures',
    'ValuationRequest',
    'InstantValueRequest',
    'ComparableProperty',
    'MarketTrends',
    'ValuationForecast',
    'ValuationResponse',
    'InstantValueResponse',
    
    # Inspection
    'InspectionType',
    'InspectionStatus',
    'InspectionSeverity',
    'InspectionItem',
    'InspectionPhoto',
    'InspectionRequest',
    'InspectionReport',
    'InspectionUpdateRequest',
    'InspectionResponse',
    'InspectionChecklist',
    
    # Instant Value
    'InstantValueBaseRequest',
    'InstantValueLocationFactors',
    'InstantValueRecentSale',
    'InstantValueMarketData',
    'InstantValueDetails',
    'InstantValueComparison',
    'InstantValueDetailedResponse',
    'InstantValueBatchRequest',
    'InstantValueBatchResponse',
    'InstantValueHistory',
    'InstantValueAccuracyMetrics',
    'DataSource',
    
    # Mileage
    'CategoryOut',
    'VariantOut',
    'RouteOut',
    'MileageClaimOut',
    'MileageClaimCreate',
    'MileageClaimUpdate',
    'MileageClaimSummary',
    'VehicleRateOut',
    'MileageApprovalRequest'
]
