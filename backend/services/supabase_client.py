# services/supabase_client.py - FIXED v6 (ENV SAFE + IMPORT SAFE)

import os
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from supabase import create_client, Client

# ─── FORCE LOAD ENV FIRST ─────────────────────────────
load_dotenv()

logger = logging.getLogger(__name__)

# ─── SAFE ENV READ (NO CRASH IMPORT-TIME) ──────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    logger.error("❌ Missing SUPABASE ENV variables")
    logger.error(f"SUPABASE_URL: {bool(SUPABASE_URL)}")
    logger.error(f"SUPABASE_ANON_KEY: {bool(SUPABASE_ANON_KEY)}")
    raise ValueError("SUPABASE environment variables not set properly")

_supabase_client: Optional[Client] = None


# ─── CLIENT SINGLETON ────────────────────────────────
def get_supabase_client() -> Client:
    global _supabase_client

    if _supabase_client is None:
        logger.info("🔌 Initializing Supabase client...")

        _supabase_client = create_client(
            SUPABASE_URL.strip(),
            SUPABASE_ANON_KEY.strip()
        )

        logger.info("✅ Supabase client ready")

    return _supabase_client


# ─── PAYMENT HELPERS ─────────────────────────────────
def create_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        client = get_supabase_client()

        payment_data.setdefault("id", str(uuid.uuid4()))
        payment_data.setdefault("status", "pending")
        payment_data["created_at"] = datetime.utcnow().isoformat()

        res = client.table("payments").insert(payment_data).execute()

        return {"success": True, "data": res.data[0]} if res.data else {
            "success": False, "error": "Insert failed"
        }

    except Exception as e:
        logger.error(f"create_payment error: {e}")
        return {"success": False, "error": str(e)}


def get_payment_by_checkout_id(checkout_id: str):
    try:
        client = get_supabase_client()
        res = client.table("payments").select("*").eq("checkout_request_id", checkout_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(e)
        return None


def update_payment(payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        client = get_supabase_client()

        update_data["updated_at"] = datetime.utcnow().isoformat()

        res = client.table("payments").update(update_data).eq("id", payment_id).execute()

        return {"success": True, "data": res.data[0]} if res.data else {
            "success": False, "error": "Not found"
        }

    except Exception as e:
        logger.error(e)
        return {"success": False, "error": str(e)}


def get_payment_by_id(payment_id: str):
    try:
        client = get_supabase_client()
        res = client.table("payments").select("*").eq("id", payment_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(e)
        return None
