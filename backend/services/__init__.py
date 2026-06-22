# services/__init__.py - Services Package

from .supabase_client import (
    get_supabase_client,
    create_payment,
    get_payment_by_id,
    get_payment_by_custom_id,
    get_payment_by_checkout_id,
    get_payment_by_mpesa_code,
    update_payment,
    update_payment_by_custom_id,
    update_payment_status,
    get_user_payments
)

from .mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    query_payment_status,
    auto_confirm_payment,
    is_mpesa_configured,
    normalize_phone,
    get_mpesa_token
)

__all__ = [
    # Supabase
    'get_supabase_client',
    'create_payment',
    'get_payment_by_id',
    'get_payment_by_custom_id',
    'get_payment_by_checkout_id',
    'get_payment_by_mpesa_code',
    'update_payment',
    'update_payment_by_custom_id',
    'update_payment_status',
    'get_user_payments',
    # M-Pesa
    'initiate_stk_push',
    'handle_mpesa_callback',
    'query_payment_status',
    'auto_confirm_payment',
    'is_mpesa_configured',
    'normalize_phone',
    'get_mpesa_token'
]
