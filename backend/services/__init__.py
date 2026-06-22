# services/__init__.py - Service Exports

from .supabase_client import (
    get_supabase_client,
    get_supabase_admin_client,
    get_supabase,
    check_health,
    create_payment,
    get_payment_by_id,
    get_payment_by_checkout_id,
    get_payment_by_mpesa_code,
    update_payment,
    update_payment_by_checkout_id,
    update_payment_status,
    get_user_payments,
    get_payments_by_status,
    get_pending_payments,
    get_payment_stats,
    delete_payment
)

from .mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    verify_payment_with_mpesa,
    query_payment_status,
    auto_confirm_payment,
    is_mpesa_configured,
    normalize_phone,
    get_mpesa_token
)

__all__ = [
    # Supabase
    'get_supabase_client',
    'get_supabase_admin_client',
    'get_supabase',
    'check_health',
    'create_payment',
    'get_payment_by_id',
    'get_payment_by_checkout_id',
    'get_payment_by_mpesa_code',
    'update_payment',
    'update_payment_by_checkout_id',
    'update_payment_status',
    'get_user_payments',
    'get_payments_by_status',
    'get_pending_payments',
    'get_payment_stats',
    'delete_payment',
    # M-Pesa
    'initiate_stk_push',
    'handle_mpesa_callback',
    'verify_payment_with_mpesa',
    'query_payment_status',
    'auto_confirm_payment',
    'is_mpesa_configured',
    'normalize_phone',
    'get_mpesa_token'
]
