# services/supabase_client.py - Supabase Client (Production Aligned v2)

import os
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────────

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is not set")

if not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_ANON_KEY is not set")


# ─── CLIENT SINGLETON ─────────────────────────────────────

_supabase_client = None
_supabase_admin_client = None


def _create_client(url: str, key: str):
    """Safe Supabase client creation (handles proxy issues)."""
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Supabase client init error: {e}")
        raise


def get_supabase_client():
    global _supabase_client

    if _supabase_client is None:
        logger.info("🔌 Initializing Supabase client")
        _supabase_client = _create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    return _supabase_client


def get_supabase():
    return get_supabase_client()


def get_supabase_admin_client():
    global _supabase_admin_client

    if _supabase_admin_client is None and SUPABASE_KEY:
        _supabase_admin_client = _create_client(SUPABASE_URL, SUPABASE_KEY)

    return _supabase_admin_client


# ─── HEALTH CHECK ─────────────────────────────────────────

def check_health():
    try:
        client = get_supabase_client()
        client.table("payments").select("id").limit(1).execute()

        return {
            "connected": True,
            "message": "Supabase OK",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ─── CREATE PAYMENT ────────────────────────────────────────

def create_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        client = get_supabase_client()

        # UUID primary key
        payment_data["id"] = str(uuid.uuid4())

        # Public reference
        if not payment_data.get("payment_id"):
            payment_data["payment_id"] = f"PAY-{uuid.uuid4().hex[:8].upper()}"

        # Required defaults
        payment_data.update({
            "status": "pending",
            "payment_method": "mpesa",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })

        res = client.table("payments").insert(payment_data).execute()

        if res.data:
            return {"success": True, "data": res.data[0]}

        return {"success": False, "error": "Insert failed"}

    except Exception as e:
        logger.error(f"Create payment error: {e}")
        return {"success": False, "error": str(e)}


# ─── GET PAYMENT (ALL METHODS ALIGNED) ─────────────────────

def get_payment_by_id(payment_uuid: str):
    client = get_supabase_client()
    res = client.table("payments").select("*").eq("id", payment_uuid).execute()
    return res.data[0] if res.data else None


def get_payment_by_payment_id(payment_id: str):
    client = get_supabase_client()
    res = client.table("payments").select("*").eq("payment_id", payment_id).execute()
    return res.data[0] if res.data else None


def get_payment_by_checkout_id(checkout_id: str):
    client = get_supabase_client()
    res = client.table("payments").select("*").eq("checkout_request_id", checkout_id).execute()
    return res.data[0] if res.data else None


def get_payment_by_mpesa_code(mpesa_code: str):
    client = get_supabase_client()
    res = client.table("payments").select("*").eq("mpesa_code", mpesa_code).execute()
    return res.data[0] if res.data else None


# ─── SINGLE UPDATE FUNCTION (SOURCE OF TRUTH) ─────────────

def update_payment(payment_uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        client = get_supabase_client()

        data["updated_at"] = datetime.now().isoformat()

        res = (
            client.table("payments")
            .update(data)
            .eq("id", payment_uuid)
            .execute()
        )

        if res.data:
            return {"success": True, "data": res.data[0]}

        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"Update payment error: {e}")
        return {"success": False, "error": str(e)}


# ─── USER PAYMENTS ─────────────────────────────────────────

def get_user_payments(user_id: str, limit: int = 50):
    try:
        client = get_supabase_client()
        res = (
            client.table("payments")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data
    except Exception as e:
        logger.error(f"User payments error: {e}")
        return []


# ─── STATUS PAYMENTS ───────────────────────────────────────

def get_payments_by_status(status: str, limit: int = 100):
    try:
        client = get_supabase_client()
        res = (
            client.table("payments")
            .select("*")
            .eq("status", status)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data
    except Exception as e:
        logger.error(f"Status query error: {e}")
        return []


# ─── STATS ─────────────────────────────────────────────────

def get_payment_stats():
    try:
        client = get_supabase_client()

        def count(status=None):
            q = client.table("payments").select("id", count="exact")
            if status:
                q = q.eq("status", status)
            return q.execute().count or 0

        return {
            "total": count(),
            "completed": count("completed"),
            "pending": count("pending"),
            "failed": count("failed"),
            "cancelled": count("cancelled"),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": str(e)}


# ─── DELETE (OPTIONAL) ─────────────────────────────────────

def delete_payment(payment_uuid: str):
    try:
        client = get_supabase_client()
        res = client.table("payments").delete().eq("id", payment_uuid).execute()

        if res.data:
            return {"success": True, "data": res.data[0]}

        return {"success": False, "error": "Not found"}

    except Exception as e:
        logger.error(f"Delete error: {e}")
        return {"success": False, "error": str(e)}


# ─── EXPORTS ──────────────────────────────────────────────

__all__ = [
    "get_supabase_client",
    "get_supabase",
    "get_supabase_admin_client",
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

    "delete_payment"
]
