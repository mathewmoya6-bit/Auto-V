# services/__init__.py
"""
AUTO-V Services Package
Contains all service integrations and business logic
"""

from .carapi_service import (
    get_carapi_service,
    decode_vin,
    get_vehicle_valuation,
    CarAPIService
)

from .supabase_client import (
    get_supabase,
    get_supabase_client,
    get_supabase_admin,
    reset_supabase_client,
    check_supabase_health,
    get_vehicle_by_vin,
    save_vin_scan
)

from .vin_validator import (
    vin_validator,
    VINValidator,
    is_valid_vin
)

from .vin_validation_service import (
    validate_vin_against_db,
    comprehensive_fraud_check,
    get_validation_service,
    VINValidationService
)

from .vin_ocr import extract_vin_from_image
from .valuation_service import valuation_service, get_valuation_service
from .openai_service import openai_service

# ─── EXPORTS ──────────────────────────────────────────────────

__all__ = [
    # CarAPI
    'get_carapi_service',
    'decode_vin',
    'get_vehicle_valuation',
    'CarAPIService',
    
    # Supabase
    'get_supabase',
    'get_supabase_client',
    'get_supabase_admin',
    'reset_supabase_client',
    'check_supabase_health',
    'get_vehicle_by_vin',
    'save_vin_scan',
    
    # VIN Validation
    'vin_validator',
    'VINValidator',
    'is_valid_vin',
    'validate_vin_against_db',
    'comprehensive_fraud_check',
    'get_validation_service',
    'VINValidationService',
    
    # OCR & Valuation
    'extract_vin_from_image',
    'valuation_service',
    'get_valuation_service',
    'openai_service',
]

# ─── MODULE INFO ─────────────────────────────────────────────

__version__ = '1.0.0'
__author__ = 'AUTO-V Team'
__description__ = 'AUTO-V Services Package'

logger.info(f"📦 Services Package v{__version__} initialized")
