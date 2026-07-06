"""
Schemas Package
Export all Pydantic models
"""

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
