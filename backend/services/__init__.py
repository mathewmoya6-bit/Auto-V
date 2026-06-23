# services/__init__.py - Production Ready v2 (FULLY ALIGNED)

from .supabase_client import (
    get_supabase_client,
    create_payment,
    get_payment_by_id,
    get_payment_by_custom_id,
    get_payment_by_checkout_id,
    get_payment_by_mpesa_code,
    update_payment,
    update_payment_by_custom_id,
    get_user_payments
)

from .mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    query_payment_status,
    normalize_phone,
    get_mpesa_token,
    is_mpesa_configured
)

from .auth_middleware import (
    verify_token,
    require_auth,
    optional_auth,
    get_current_user,
    generate_token,
    verify_supabase_token
)

__all__ = [
    # Supabase
    "get_supabase_client",
    "create_payment",
    "get_payment_by_id",
    "get_payment_by_custom_id",
    "get_payment_by_checkout_id",
    "get_payment_by_mpesa_code",
    "update_payment",
    "update_payment_by_custom_id",
    "get_user_payments",
    
    # M-Pesa
    "initiate_stk_push",
    "handle_mpesa_callback",
    "query_payment_status",
    "normalize_phone",
    "get_mpesa_token",
    "is_mpesa_configured",
    
    # Auth
    "verify_token",
    "require_auth",
    "optional_auth",
    "get_current_user",
    "generate_token",
    "verify_supabase_token"
]
