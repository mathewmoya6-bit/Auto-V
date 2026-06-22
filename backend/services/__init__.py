# services/__init__.py - Service Exports (Aligned v2)

# ─── SUPABASE CORE ─────────────────────────────────────────

from .supabase_client import (
    get_supabase_client,
    get_supabase_admin_client,
    get_supabase,
    check_health,
    create_payment,
    get_payment_by_id,
    get_payment_by_payment_id,
    get_payment_by_checkout_id,
    get_payment_by_mpesa_code,
    update_payment,
    get_user_payments,
    get_payments_by_status,
    get_payment_stats,
    delete_payment
)

# ─── M-PESA CORE ────────────────────────────────────────────

from .mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    verify_payment_with_mpesa,
    query_payment_status,
    auto_confirm_payment,
    force_complete_payment,
    is_mpesa_configured,
    normalize_phone,
    get_mpesa_token
)

# ─── EXPORTS (SINGLE SOURCE OF TRUTH) ──────────────────────

__all__ = [

    # ── SUPABASE ───────────────────────────────────────────
    "get_supabase_client",
    "get_supabase_admin_client",
    "get_supabase",
    "check_health",

    "create_payment",

    "get_payment_by_id",
    "get_payment_by_payment_id",
    "get_payment_by_checkout_id",
    "get_payment_by_mpesa_code",

    "update_payment",

    "get_user_payments",
    "get_payments_by_status",
    "get_payment_stats",

    "delete_payment",

    # ── M-PESA ─────────────────────────────────────────────
    "initiate_stk_push",
    "handle_mpesa_callback",
    "verify_payment_with_mpesa",
    "query_payment_status",
    "auto_confirm_payment",
    "force_complete_payment",
    "is_mpesa_configured",
    "normalize_phone",
    "get_mpesa_token"
]
