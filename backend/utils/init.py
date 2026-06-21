# utils/__init__.py
"""
Utility functions for AUTO-V backend
"""

from .decorators import (
    rate_limit,
    require_auth,
    log_request,
    handle_errors,
    retry_on_failure
)

from .validators import (
    validate_email,
    validate_phone,
    validate_vin,
    validate_vin_format,
    validate_odometer,
    validate_amount,
    validate_date
)

from .helpers import (
    generate_id,
    generate_reference,
    format_currency,
    calculate_age,
    get_current_time,
    sanitize_string
)

from .logger import setup_logging, get_logger

__all__ = [
    # Decorators
    'rate_limit',
    'require_auth',
    'log_request',
    'handle_errors',
    'retry_on_failure',
    
    # Validators
    'validate_email',
    'validate_phone',
    'validate_vin',
    'validate_vin_format',
    'validate_odometer',
    'validate_amount',
    'validate_date',
    
    # Helpers
    'generate_id',
    'generate_reference',
    'format_currency',
    'calculate_age',
    'get_current_time',
    'sanitize_string',
    
    # Logger
    'setup_logging',
    'get_logger'
]
