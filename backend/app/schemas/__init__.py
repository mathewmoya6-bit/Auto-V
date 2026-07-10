# app/schemas/__init__.py
from .auth import (
    UserLogin,
    UserRegister,
    TokenResponse,
    RefreshRequest,
    UserResponse
)
from .user import UserProfile
from .valuation import (
    ValuationRequest,
    ValuationCreate,
    ValuationUpdate,
    ValuationResponse,
    ValuationHistory,
    ValuationStats,
    InstantValueRequest,
    InstantValueResponse
)
from .vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
    VehicleDetailResponse
)

__all__ = [
    # Auth
    "UserLogin",
    "UserRegister",
    "TokenResponse",
    "RefreshRequest",
    "UserResponse",
    
    # User
    "UserProfile",
    
    # Valuation
    "ValuationRequest",
    "ValuationCreate",
    "ValuationUpdate",
    "ValuationResponse",
    "ValuationHistory",
    "ValuationStats",
    "InstantValueRequest",
    "InstantValueResponse",
    
    # Vehicle
    "VehicleCreate",
    "VehicleUpdate",
    "VehicleResponse",
    "VehicleDetailResponse"
]
