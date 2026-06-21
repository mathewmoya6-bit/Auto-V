# services/__init__.py - AUTO-V Services Package
"""
AUTO-V Services Package
Exports all service modules for easy import
"""

# ─── Supabase Client ──────────────────────────────────────────
from .supabase_client import (
    get_supabase_client,
    get_supabase_admin,
    reset_supabase_client,
    get_supabase,
    check_supabase_health,
    get_vehicle_by_vin,
    get_vehicles_by_user,
    create_vehicle,
    update_vehicle,
    save_vin_scan,
    get_vin_scans,
    save_service_request,
    get_service_requests,
    get_service_request,
    save_transaction,
    update_transaction_status,
    get_stats,
    get_system_settings,
    update_system_settings
)

# ─── VIN Validator ────────────────────────────────────────────
from .vin_validator import (
    is_valid_vin,
    vin_validator,
    VINValidator
)

# ─── VIN OCR ──────────────────────────────────────────────────
try:
    from .vin_ocr import extract_vin_from_image
except ImportError:
    extract_vin_from_image = None

# ─── CarAPI Service ───────────────────────────────────────────
try:
    from .carapi_service import (
        get_carapi_service,
        decode_vin,
        get_vehicle_valuation,
        CarAPIService
    )
except ImportError:
    get_carapi_service = None
    decode_vin = None
    get_vehicle_valuation = None
    CarAPIService = None

# ─── Valuation Engine ─────────────────────────────────────────
try:
    from .valuation_engine import calculate_value, quick_estimate
except ImportError:
    calculate_value = None
    quick_estimate = None

# ─── Inspection Engine ────────────────────────────────────────
try:
    from .inspection_engine import calculate_inspection, quick_inspection
except ImportError:
    calculate_inspection = None
    quick_inspection = None

# ─── Assessment Engine ────────────────────────────────────────
try:
    from .assessment_engine import assess, get_assessment_price
except ImportError:
    assess = None
    get_assessment_price = None

# ─── Mileage Engine ───────────────────────────────────────────
try:
    from .mileage_engine import calculate_mileage_rate, get_default_fuel_economy
except ImportError:
    calculate_mileage_rate = None
    get_default_fuel_economy = None

# ─── Fraud Detection ──────────────────────────────────────────
try:
    from .fraud_detection import check_fraud, get_fraud_score
except ImportError:
    check_fraud = None
    get_fraud_score = None

# ─── Export All ──────────────────────────────────────────────

__all__ = [
    # Supabase Client
    'get_supabase_client',
    'get_supabase_admin',
    'reset_supabase_client',
    'get_supabase',
    'check_supabase_health',
    'get_vehicle_by_vin',
    'get_vehicles_by_user',
    'create_vehicle',
    'update_vehicle',
    'save_vin_scan',
    'get_vin_scans',
    'save_service_request',
    'get_service_requests',
    'get_service_request',
    'save_transaction',
    'update_transaction_status',
    'get_stats',
    'get_system_settings',
    'update_system_settings',
    
    # VIN Validator
    'is_valid_vin',
    'vin_validator',
    'VINValidator',
    
    # VIN OCR
    'extract_vin_from_image',
    
    # CarAPI
    'get_carapi_service',
    'decode_vin',
    'get_vehicle_valuation',
    'CarAPIService',
    
    # Valuation
    'calculate_value',
    'quick_estimate',
    
    # Inspection
    'calculate_inspection',
    'quick_inspection',
    
    # Assessment
    'assess',
    'get_assessment_price',
    
    # Mileage
    'calculate_mileage_rate',
    'get_default_fuel_economy',
    
    # Fraud
    'check_fraud',
    'get_fraud_score'
]

# ─── Package Info ─────────────────────────────────────────────

__version__ = '1.0.0'
__author__ = 'AUTO-V Team'
__description__ = 'AUTO-V Services Package'

import logging
logger = logging.getLogger(__name__)
logger.info(f"📦 Services Package v{__version__} initialized")
