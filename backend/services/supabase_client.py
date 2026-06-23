# services/supabase_client.py - Production Ready v6

import os
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ─── ENV FIX (SAFE + STRIPPED) ─────────────────────────────

SUPABASE_URL = (os.getenv('SUPABASE_URL') or '').strip()
SUPABASE_ANON_KEY = (os.getenv('SUPABASE_ANON_KEY') or '').strip()

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable is not set")

if not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_ANON_KEY environment variable is not set")

_supabase_client = None


# ─── CLIENT ────────────────────────────────────────────────

def get_supabase_client() -> Client:
    global _supabase_client

    if _supabase_client is None:
        logger.info("🔌 Initializing Supabase client...")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("✅ Supabase client ready")

    return _supabase_client


# ─── PAYMENT CREATE ───────────────────────────────────────

def create_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        client = get_supabase_client()

        payment_data.setdefault("id", str(uuid.uuid4()))
        payment_data.setdefault("status", "pending")
        payment_data.setdefault("payment_method", "mpesa")
        payment_data.setdefault("created_at", datetime.utcnow().isoformat())
        payment_data["updated_at"] = datetime.utcnow().isoformat()

        res = client.table("payments").insert(payment_data).execute()

        return {"success": True, "data": res.data[0]} if res.data else {"success": False}

    except Exception as e:
        logger.error(f"create_payment error: {e}")
        return {"success": False, "error": str(e)}


# ─── READ HELPERS ─────────────────────────────────────────

def get_payment_by_id(payment_id: str):
    client = get_supabase_client()
    res = client.table("payments").select("*").eq("id", payment_id).execute()
    return res.data[0] if res.data else None


def get_payment_by_custom_id(payment_id: str):
    client = get_supabase_client()
    res = client.table("payments").select("*").eq("payment_id", payment_id).execute()
    return res.data[0] if res.data else None


def get_payment_by_checkout_id(checkout_id: str):
    client = get_supabase_client()
    res = client.table("payments").select("*").eq("checkout_request_id", checkout_id).execute()
    return res.data[0] if res.data else None


def get_payment_by_mpesa_code(code: str):
    client = get_supabase_client()
    res = client.table("payments").select("*").eq("mpesa_code", code).execute()
    return res.data[0] if res.data else None


# ✅ FIX: missing function (THIS WAS YOUR ERROR)
def update_payment_by_custom_id(payment_id: str, update_data: Dict[str, Any]):
    client = get_supabase_client()
    update_data["updated_at"] = datetime.utcnow().isoformat()

    res = client.table("payments") \
        .update(update_data) \
        .eq("payment_id", payment_id) \
        .execute()

    return {"success": bool(res.data), "data": res.data}


def update_payment(payment_id: str, update_data: Dict[str, Any]):
    client = get_supabase_client()
    update_data["updated_at"] = datetime.utcnow().isoformat()

    res = client.table("payments") \
        .update(update_data) \
        .eq("id", payment_id) \
        .execute()

    return {"success": bool(res.data), "data": res.data}


def get_user_payments(user_id: str, limit: int = 50):
    client = get_supabase_client()
    res = (
        client.table("payments")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


__all__ = [
    "get_supabase_client",
    "create_payment",
    "get_payment_by_id",
    "get_payment_by_custom_id",
    "get_payment_by_checkout_id",
    "get_payment_by_mpesa_code",
    "update_payment",
    "update_payment_by_custom_id",
    "get_user_payments",
]
