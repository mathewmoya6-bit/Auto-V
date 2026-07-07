# app/schemas/__init__.py
# =============================================================================
# AUTO-V API - Schemas Package
# =============================================================================

from app.schemas.auth import (
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
)
from app.schemas.user import UserProfile, UserUpdate
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
    VehicleImage,
    VehicleImageCreate,
    VINScan,
    VINScanCreate,
    VINScanResponse,
)
from app.schemas.mileage import (
    VehicleCategoryCreate,
    VehicleCategoryResponse,
    VehicleVariantCreate,
    VehicleVariantResponse,
    RouteCreate,
    RouteResponse,
    MileageClaimCreate,
    MileageClaimResponse,
)
from app.schemas.valuation import (
    ValuationCreate,
    ValuationUpdate,
    ValuationResponse,
    InstantValuationRequest,
    InstantValuationResponse,
)
from app.schemas.inspection import (
    InspectionCreate,
    InspectionUpdate,
    InspectionResponse,
)
from app.schemas.fleet import (
    FleetCreate,
    FleetUpdate,
    FleetResponse,
)
from app.schemas.certificate import (
    CertificateCreate,
    CertificateUpdate,
    CertificateResponse,
)
from app.schemas.payment import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    MpesaPaymentRequest,
    MpesaPaymentResponse,
)

__all__ = [
    # Auth
    "UserCreate",
    "UserLogin",
    "TokenResponse",
    "UserResponse",
    
    # User
    "UserProfile",
    "UserUpdate",
    
    # Vehicle
    "VehicleCreate",
    "VehicleUpdate",
    "VehicleResponse",
    "VehicleImage",
    "VehicleImageCreate",
    "VINScan",
    "VINScanCreate",
    "VINScanResponse",
    
    # Mileage
    "VehicleCategoryCreate",
    "VehicleCategoryResponse",
    "VehicleVariantCreate",
    "VehicleVariantResponse",
    "RouteCreate",
    "RouteResponse",
    "MileageClaimCreate",
    "MileageClaimResponse",
    
    # Valuation
    "ValuationCreate",
    "ValuationUpdate",
    "ValuationResponse",
    "InstantValuationRequest",
    "InstantValuationResponse",
    
    # Inspection
    "InspectionCreate",
    "InspectionUpdate",
    "InspectionResponse",
    
    # Fleet
    "FleetCreate",
    "FleetUpdate",
    "FleetResponse",
    
    # Certificate
    "CertificateCreate",
    "CertificateUpdate",
    "CertificateResponse",
    
    # Payment
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentResponse",
    "MpesaPaymentRequest",
    "MpesaPaymentResponse",
]
