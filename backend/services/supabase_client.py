import os
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

_supabase = None


def get_supabase_client():
    global _supabase

    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    return _supabase


# ─── CREATE PAYMENT ─────────────────────────────
def create_payment(data: dict):
    try:
        client = get_supabase_client()

        if not data.get("payment_id"):
            data["payment_id"] = f"PAY-{uuid.uuid4().hex[:8].upper()}"

        data["status"] = data.get("status", "pending")
        data["created_at"] = datetime.now().isoformat()
        data["updated_at"] = datetime.now().isoformat()

        res = client.table("payments").insert(data).execute()

        if res.data:
            return {"success": True, "data": res.data[0]}

        logger.error(f"Insert failed: {res}")
        return {"success": False, "error": str(res)}

    except Exception as e:
        logger.error(f"create_payment error: {e}")
        return {"success": False, "error": str(e)}


# ─── GET BY ID ─────────────────────────────
def get_payment_by_id(id: str):
    client = get_supabase_client()
    res = client.table("payments").select("*").eq("id", id).execute()
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


# ─── UPDATE ─────────────────────────────
def update_payment(id: str, data: dict):
    client = get_supabase_client()
    data["updated_at"] = datetime.now().isoformat()

    res = client.table("payments").update(data).eq("id", id).execute()

    return {"success": bool(res.data), "data": res.data}
