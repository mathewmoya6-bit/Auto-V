# services/supabase_client.py - Production Ready v8 (Clean & Reliable)

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
SUPABASE_SERVICE_ROLE_KEY = (os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY') or '').strip()

_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable is not set")

# Don't raise error for missing keys - we'll handle gracefully


# ─── CLIENT ────────────────────────────────────────────────────

def get_supabase_client(use_service_role: bool = False) -> Client:
    """
    Get or create singleton Supabase client.
    
    Args:
        use_service_role: If True, use service role key (for admin operations)
    
    Returns:
        Supabase Client instance
    """
    global _supabase_client, _supabase_admin_client
    
    if use_service_role:
        if _supabase_admin_client is None:
            key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
            if not key:
                raise ValueError("No Supabase key available for admin client")
            
            logger.info("🔌 Initializing Supabase admin client (service role)")
            _supabase_admin_client = create_client(SUPABASE_URL, key)
            logger.info("✅ Supabase admin client initialized")
        
        return _supabase_admin_client
    
    if _supabase_client is None:
        if not SUPABASE_ANON_KEY:
            raise ValueError("SUPABASE_ANON_KEY environment variable is not set")
        
        logger.info("🔌 Initializing Supabase client (anon key)")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("✅ Supabase client initialized")
    
    return _supabase_client


def get_admin_client() -> Client:
    """Get admin client with service role (for writes, callbacks, admin ops)."""
    return get_supabase_client(use_service_role=True)


# ─── PAYMENT CREATE ──────────────────────────────────────────

def create_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new payment record using admin client (bypasses RLS)."""
    try:
        # Use admin client for writes to avoid RLS issues
        client = get_admin_client()
        now = datetime.now(timezone.utc).isoformat()

        # Ensure 'id' is always a valid UUID
        if 'id' not in payment_data or not payment_data['id']:
            payment_data['id'] = str(uuid.uuid4())
        else:
            try:
                uuid.UUID(str(payment_data['id']))
            except ValueError:
                if 'payment_id' not in payment_data or not payment_data['payment_id']:
                    payment_data['payment_id'] = str(payment_data['id'])
                payment_data['id'] = str(uuid.uuid4())

        # Ensure payment_id exists
        if 'payment_id' not in payment_data or not payment_data['payment_id']:
            payment_data['payment_id'] = f"PAY-{uuid.uuid4().hex[:8].upper()}"

        # Set defaults
        payment_data.setdefault("status", "pending")
        payment_data.setdefault("payment_method", "mpesa")
        payment_data.setdefault("created_at", now)
        payment_data["updated_at"] = now

        logger.info(f"📝 Creating payment: {payment_data['payment_id']}")

        result = client.table("payments").insert(payment_data).execute()

        if result.data:
            logger.info(f"✅ Payment created: {result.data[0].get('payment_id')}")
            return {"success": True, "data": result.data[0]}

        logger.warning("create_payment: No data returned")
        return {"success": False, "error": "No data returned"}

    except Exception as e:
        logger.error(f"create_payment error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─── READ HELPERS ─────────────────────────────────────────────

def get_payment_by_id(payment_id: str, use_admin: bool = False) -> Optional[Dict[str, Any]]:
    """Get payment by UUID primary key."""
    try:
        client = get_admin_client() if use_admin else get_supabase_client()
        result = client.table("payments").select("*").eq("id", payment_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_id error: {e}", exc_info=True)
        return None


def get_payment_by_custom_id(payment_id: str, use_admin: bool = False) -> Optional[Dict[str, Any]]:
    """Get payment by custom payment_id field."""
    try:
        client = get_admin_client() if use_admin else get_supabase_client()
        result = client.table("payments").select("*").eq("payment_id", payment_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_custom_id error: {e}", exc_info=True)
        return None


def get_payment_by_checkout_id(checkout_id: str, use_admin: bool = False) -> Optional[Dict[str, Any]]:
    """Get payment by M-Pesa CheckoutRequestID."""
    try:
        client = get_admin_client() if use_admin else get_supabase_client()
        result = client.table("payments").select("*").eq("checkout_request_id", checkout_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_checkout_id error: {e}", exc_info=True)
        return None


def get_payment_by_mpesa_code(code: str, use_admin: bool = False) -> Optional[Dict[str, Any]]:
    """Get payment by M-Pesa receipt number."""
    try:
        client = get_admin_client() if use_admin else get_supabase_client()
        result = client.table("payments").select("*").eq("mpesa_code", code).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_payment_by_mpesa_code error: {e}", exc_info=True)
        return None


def get_payment_by_any_id(identifier: str, use_admin: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get payment by any identifier type.
    
    Tries in order:
    1. payment_id (custom string)
    2. checkout_request_id
    3. mpesa_code
    4. id (UUID)
    """
    try:
        # Try custom payment_id first
        payment = get_payment_by_custom_id(identifier, use_admin)
        if payment:
            return payment

        # Try checkout_request_id
        payment = get_payment_by_checkout_id(identifier, use_admin)
        if payment:
            return payment

        # Try mpesa_code
        payment = get_payment_by_mpesa_code(identifier, use_admin)
        if payment:
            return payment

        # Try UUID
        try:
            uuid.UUID(identifier)
            payment = get_payment_by_id(identifier, use_admin)
            if payment:
                return payment
        except ValueError:
            pass

        return None

    except Exception as e:
        logger.error(f"get_payment_by_any_id error: {e}", exc_info=True)
        return None


# ─── UPDATE FUNCTIONS ─────────────────────────────────────────

def update_payment(payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update payment by UUID primary key using admin client (bypasses RLS)."""
    try:
        client = get_admin_client()
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = client.table("payments") \
            .update(update_data) \
            .eq("id", payment_id) \
            .execute()

        if result.data:
            logger.info(f"✅ Payment updated: {payment_id}")
            return {"success": True, "data": result.data[0]}

        logger.warning(f"update_payment: No data for ID {payment_id}")
        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"update_payment error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def update_payment_by_custom_id(payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update payment by custom payment_id field using admin client."""
    try:
        client = get_admin_client()
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = client.table("payments") \
            .update(update_data) \
            .eq("payment_id", payment_id) \
            .execute()

        if result.data:
            logger.info(f"✅ Payment updated by custom ID: {payment_id}")
            return {"success": True, "data": result.data[0]}

        logger.warning(f"update_payment_by_custom_id: No data for {payment_id}")
        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"update_payment_by_custom_id error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def update_payment_by_checkout_id(checkout_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update payment by checkout_request_id using admin client."""
    try:
        client = get_admin_client()
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = client.table("payments") \
            .update(update_data) \
            .eq("checkout_request_id", checkout_id) \
            .execute()

        if result.data:
            logger.info(f"✅ Payment updated by checkout ID: {checkout_id}")
            return {"success": True, "data": result.data[0]}

        logger.warning(f"update_payment_by_checkout_id: No data for {checkout_id}")
        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"update_payment_by_checkout_id error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def update_payment_status(payment_id: str, status: str, extra_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Update payment status by UUID primary key using admin client."""
    try:
        client = get_admin_client()
        now = datetime.now(timezone.utc).isoformat()

        update_data = {
            "status": status,
            "updated_at": now
        }

        if status == "completed":
            update_data["paid_at"] = now

        if extra_data:
            update_data.update(extra_data)

        result = client.table("payments") \
            .update(update_data) \
            .eq("id", payment_id) \
            .execute()

        if result.data:
            logger.info(f"✅ Payment status updated: {payment_id} → {status}")
            return {"success": True, "data": result.data[0]}

        logger.warning(f"update_payment_status: No data for {payment_id}")
        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"update_payment_status error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def update_payment_status_by_custom_id(payment_id: str, status: str, extra_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Update payment status by custom payment_id field using admin client."""
    try:
        client = get_admin_client()
        now = datetime.now(timezone.utc).isoformat()

        update_data = {
            "status": status,
            "updated_at": now
        }

        if status == "completed":
            update_data["paid_at"] = now

        if extra_data:
            update_data.update(extra_data)

        result = client.table("payments") \
            .update(update_data) \
            .eq("payment_id", payment_id) \
            .execute()

        if result.data:
            logger.info(f"✅ Payment status updated by custom ID: {payment_id} → {status}")
            return {"success": True, "data": result.data[0]}

        logger.warning(f"update_payment_status_by_custom_id: No data for {payment_id}")
        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"update_payment_status_by_custom_id error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def update_payment_with_transaction(payment_id: str, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update payment with M-Pesa transaction data using admin client."""
    try:
        client = get_admin_client()
        now = datetime.now(timezone.utc).isoformat()

        update_data = {
            "status": "completed",
            "mpesa_code": transaction_data.get("mpesa_code"),
            "transaction_id": transaction_data.get("mpesa_code"),
            "mpesa_result_code": "0",
            "mpesa_result_desc": "Transaction completed",
            "paid_at": now,
            "updated_at": now
        }

        if transaction_data.get("amount"):
            update_data["amount"] = transaction_data.get("amount")

        if transaction_data.get("phone"):
            update_data["mpesa_phone"] = transaction_data.get("phone")

        result = client.table("payments") \
            .update(update_data) \
            .eq("id", payment_id) \
            .execute()

        if result.data:
            logger.info(f"✅ Payment transaction updated: {payment_id}")
            return {"success": True, "data": result.data[0]}

        logger.warning(f"update_payment_with_transaction: No data for {payment_id}")
        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"update_payment_with_transaction error: {e}", exc_info=True)
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


def get_payments_by_status(status: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get payments by status."""
    try:
        client = get_supabase_client()
        result = (
            client.table("payments")
            .select("*")
            .eq("status", status)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"get_payments_by_status error: {e}", exc_info=True)
        return []


def get_pending_payments(limit: int = 50) -> List[Dict[str, Any]]:
    """Get pending payments that need verification."""
    try:
        client = get_supabase_client()
        result = (
            client.table("payments")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"get_pending_payments error: {e}", exc_info=True)
        return []


def get_payment_stats() -> Dict[str, Any]:
    """Get payment statistics."""
    try:
        client = get_supabase_client()

        total = client.table("payments").select("count", count="exact").execute()
        completed = client.table("payments").select("count", count="exact").eq("status", "completed").execute()
        pending = client.table("payments").select("count", count="exact").eq("status", "pending").execute()
        failed = client.table("payments").select("count", count="exact").eq("status", "failed").execute()
        cancelled = client.table("payments").select("count", count="exact").eq("status", "cancelled").execute()

        return {
            "total": total.count if hasattr(total, "count") else 0,
            "completed": completed.count if hasattr(completed, "count") else 0,
            "pending": pending.count if hasattr(pending, "count") else 0,
            "failed": failed.count if hasattr(failed, "count") else 0,
            "cancelled": cancelled.count if hasattr(cancelled, "count") else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"get_payment_stats error: {e}", exc_info=True)
        return {"error": str(e)}


# ─── DELETE FUNCTIONS ──────────────────────────────────────────

def delete_payment(payment_id: str) -> Dict[str, Any]:
    """Delete a payment record by UUID primary key (use with caution)."""
    try:
        client = get_admin_client()
        result = client.table("payments").delete().eq("id", payment_id).execute()

        if result.data:
            logger.info(f"✅ Payment deleted: {payment_id}")
            return {"success": True, "data": result.data[0]}

        logger.warning(f"delete_payment: No data for {payment_id}")
        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"delete_payment error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def delete_payment_by_custom_id(payment_id: str) -> Dict[str, Any]:
    """Delete a payment record by custom payment_id field (use with caution)."""
    try:
        client = get_admin_client()
        result = client.table("payments").delete().eq("payment_id", payment_id).execute()

        if result.data:
            logger.info(f"✅ Payment deleted by custom ID: {payment_id}")
            return {"success": True, "data": result.data[0]}

        logger.warning(f"delete_payment_by_custom_id: No data for {payment_id}")
        return {"success": False, "error": "Payment not found"}

    except Exception as e:
        logger.error(f"delete_payment_by_custom_id error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─── HEALTH STATUS ────────────────────────────────────────────

def get_connection_status() -> Dict[str, Any]:
    """
    Get connection status WITHOUT testing database tables.
    
    This is a clean health check that doesn't depend on:
    - Table existence
    - RLS policies
    - Database schema
    """
    return {
        "initialized": _supabase_client is not None,
        "admin_initialized": _supabase_admin_client is not None,
        "url_configured": bool(SUPABASE_URL),
        "anon_key_configured": bool(SUPABASE_ANON_KEY),
        "service_role_configured": bool(SUPABASE_KEY),
        "key_mode": (
            "service_role"
            if SUPABASE_KEY and _supabase_admin_client is not None
            else "anon"
            if _supabase_client is not None
            else "uninitialized"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ─── EXPORTS ──────────────────────────────────────────────────

__all__ = [
    # Client
    "get_supabase_client",
    "get_admin_client",

    # Create
    "create_payment",

    # Read
    "get_payment_by_id",
    "get_payment_by_custom_id",
    "get_payment_by_checkout_id",
    "get_payment_by_mpesa_code",
    "get_payment_by_any_id",

    # Update
    "update_payment",
    "update_payment_by_custom_id",
    "update_payment_by_checkout_id",
    "update_payment_status",
    "update_payment_status_by_custom_id",
    "update_payment_with_transaction",

    # Query
    "get_user_payments",
    "get_payments_by_status",
    "get_pending_payments",
    "get_payment_stats",

    # Delete
    "delete_payment",
    "delete_payment_by_custom_id",

    # Health
    "get_connection_status"
]
