# ============================================================
# services/supabase_client.py - Supabase Client Wrapper
# ============================================================

import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# ─── Singleton Client ──────────────────────────────────────
_supabase_client = None


def get_supabase_client():
    """Get Supabase client instance (singleton)."""
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    try:
        from supabase import create_client
        
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase client initialized")
        return _supabase_client
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
        raise


# ─── Payment CRUD Operations ──────────────────────────────

def get_payment_by_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by UUID."""
    try:
        client = get_supabase_client()
        result = client.table("payments").select("*").eq("id", payment_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_id error: {e}")
        return None


def get_payment_by_checkout_id(checkout_request_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by checkout_request_id."""
    try:
        client = get_supabase_client()
        result = client.table("payments").select("*").eq("checkout_request_id", checkout_request_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_checkout_id error: {e}")
        return None


def get_payment_by_mpesa_code(mpesa_code: str) -> Optional[Dict[str, Any]]:
    """Get payment by M-Pesa receipt code."""
    try:
        client = get_supabase_client()
        result = client.table("payments").select("*").eq("mpesa_code", mpesa_code).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_mpesa_code error: {e}")
        return None


def update_payment(payment_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update payment by ID."""
    try:
        client = get_supabase_client()
        result = client.table("payments").update(data).eq("id", payment_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"update_payment error: {e}")
        return None


def update_payment_by_checkout_id(checkout_request_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update payment by checkout_request_id."""
    try:
        client = get_supabase_client()
        result = client.table("payments").update(data).eq("checkout_request_id", checkout_request_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"update_payment_by_checkout_id error: {e}")
        return None


def get_user_payments(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all payments for a user."""
    try:
        client = get_supabase_client()
        result = client.table("payments").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"get_user_payments error: {e}")
        return []
