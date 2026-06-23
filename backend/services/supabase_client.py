# services/supabase_client.py - Production Ready v7 (Clean & Aligned)

import os
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ─── CONFIGURATION ─────────────────────────────────────────────

SUPABASE_URL = (os.getenv('SUPABASE_URL') or '').strip()
SUPABASE_ANON_KEY = (os.getenv('SUPABASE_ANON_KEY') or '').strip()
_supabase_client: Optional[Client] = None


# ─── CLIENT ────────────────────────────────────────────────────

def get_supabase_client() -> Client:
    """Get or create singleton Supabase client."""
    global _supabase_client

    if _supabase_client is None:
        logger.info("🔌 Initializing Supabase client...")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("✅ Supabase client ready")

    return _supabase_client


# ─── PAYMENT CREATE ──────────────────────────────────────────

def create_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new payment record."""
    try:
        client = get_supabase_client()
        now = datetime.now(timezone.utc).isoformat()

        payment_data.setdefault("id", str(uuid.uuid4()))
        payment_data.setdefault("status", "pending")
        payment_data.setdefault("payment_method", "mpesa")
        payment_data.setdefault("created_at", now)
        payment_data["updated_at"] = now

        result = client.table("payments").insert(payment_data).execute()

        if result.data:
            return {"success": True, "data": result.data[0]}

        logger.warning("create_payment: No data returned")
        return {"success": False, "error": "No data returned"}

    except Exception as e:
        logger.error(f"create_payment error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─── READ HELPERS ─────────────────────────────────────────────

def get_payment_by_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by UUID primary key."""
    try:
        client = get_supabase_client()
        result = client.table("payments").select("*").eq("id", payment_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_id error: {e}", exc_info=True)
        return None


def get_payment_by_custom_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by custom payment_id field."""
    try:
        client = get_supabase_client()
        result = client.table("payments").select("*").eq("payment_id", payment_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_custom_id error: {e}", exc_info=True)
        return None


def get_payment_by_checkout_id(checkout_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by M-Pesa CheckoutRequestID."""
    try:
        client = get_supabase_client()
        result = client.table("payments").select("*").eq("checkout_request_id", checkout_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_checkout_id error: {e}", exc_info=True)
        return None


def get_payment_by_mpesa_code(code: str) -> Optional[Dict[str, Any]]:
    """Get payment by M-Pesa receipt number."""
    try:
        client = get_supabase_client()
        result = client.table("payments").select("*").eq("mpesa_code", code).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_mpesa_code error: {e}", exc_info=True)
        return None


# ─── UPDATE FUNCTIONS ─────────────────────────────────────────

def update_payment(payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update payment by UUID primary key."""
    try:
        client = get_supabase_client()
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = client.table("payments") \
            .update(update_data) \
            .eq("id", payment_id) \
            .execute()

        if result.data:
            return {"success": True, "data": result.data}

        logger.warning(f"update_payment: No data for ID {payment_id}")
        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"update_payment error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def update_payment_by_custom_id(payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update payment by custom payment_id field."""
    try:
        client = get_supabase_client()
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = client.table("payments") \
            .update(update_data) \
            .eq("payment_id", payment_id) \
            .execute()

        if result.data:
            return {"success": True, "data": result.data}

        logger.warning(f"update_payment_by_custom_id: No data for {payment_id}")
        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"update_payment_by_custom_id error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─── USER PAYMENTS ────────────────────────────────────────────

def get_user_payments(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all payments for a specific user."""
    try:
        client = get_supabase_client()
        result = (
            client.table("payments")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"get_user_payments error: {e}", exc_info=True)
        return []


# ─── EXPORTS ──────────────────────────────────────────────────

__all__ = [
    "get_supabase_client",
    "create_payment",
    "get_payment_by_id",
    "get_payment_by_custom_id",
    "get_payment_by_checkout_id",
    "get_payment_by_mpesa_code",
    "update_payment",
    "update_payment_by_custom_id",
    "get_user_payments"
]
