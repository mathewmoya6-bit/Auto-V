# ============================================================
# services/supabase_client.py - Supabase Client Wrapper
# ============================================================

import os
import logging
import importlib
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

_supabase_client = None


def log_supabase_version():
    """Log the version of supabase and httpx being used."""
    try:
        # Check supabase version
        import supabase
        logger.info(f"📦 SUPABASE VERSION: {supabase.__version__}")
    except (ImportError, AttributeError) as e:
        logger.warning(f"⚠️ Could not get supabase version: {e}")
    
    try:
        # Check httpx version
        import httpx
        logger.info(f"📦 HTTPX VERSION: {httpx.__version__}")
    except (ImportError, AttributeError) as e:
        logger.warning(f"⚠️ Could not get httpx version: {e}")


def get_supabase_client():
    """Get Supabase client instance (singleton)."""
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    try:
        # Log versions first
        log_supabase_version()
        
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        
        logger.info(f"🔗 Connecting to Supabase: {SUPABASE_URL}")
        
        # Try different import methods based on version
        try:
            # Method 1: Standard import (most common)
            from supabase import create_client
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            logger.info("✅ Supabase client initialized (standard method)")
            
        except TypeError as e:
            if "proxy" in str(e):
                logger.warning("⚠️ Proxy parameter issue, trying alternative method...")
                # Method 2: For newer versions without proxy
                from supabase.client import Client
                _supabase_client = Client(SUPABASE_URL, SUPABASE_ANON_KEY)
                logger.info("✅ Supabase client initialized (alternative method - no proxy)")
            else:
                raise
                
        except ImportError as e:
            logger.warning(f"⚠️ Standard import failed: {e}")
            # Method 3: Old import style (supabase-py)
            try:
                from supabase_py import create_client
                _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
                logger.info("✅ Supabase client initialized (old import style - supabase-py)")
            except ImportError:
                # Method 4: Try importing from supabase.client directly
                from supabase.client import Client
                _supabase_client = Client(SUPABASE_URL, SUPABASE_ANON_KEY)
                logger.info("✅ Supabase client initialized (direct Client import)")
        
        # Verify the client works with a simple query
        try:
            test_result = (
                _supabase_client.table("payments")
                .select("payment_id")
                .limit(1)
                .execute()
            )
            logger.info("✅ Supabase client verified with test query")
        except Exception as test_e:
            logger.warning(f"⚠️ Test query failed but client created: {test_e}")
        
        return _supabase_client
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
        import traceback
        traceback.print_exc()
        raise


# ─── Payment CRUD Operations ──────────────────────────────

def create_payment(payment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a new payment record in Supabase.
    
    Args:
        payment_data: Dictionary with payment fields
        
    Returns:
        Created payment record or None if failed
    """
    try:
        client = get_supabase_client()
        
        # Ensure created_at is set
        if "created_at" not in payment_data:
            payment_data["created_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"💾 Creating payment: {payment_data.get('payment_id')}")
        logger.debug(f"Payment data: {payment_data}")
        
        result = (
            client.table("payments")
            .insert(payment_data)
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            logger.info(f"✅ Payment created: {result.data[0].get('payment_id')}")
            return result.data[0]
        else:
            logger.error("❌ No data returned from create_payment")
            return None
            
    except Exception as e:
        logger.error(f"❌ create_payment error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_payment_by_payment_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a payment by its payment_id.
    
    Args:
        payment_id: The payment ID
        
    Returns:
        Payment record or None if not found
    """
    try:
        client = get_supabase_client()
        
        result = (
            client.table("payments")
            .select("*")
            .eq("payment_id", payment_id)
            .limit(1)
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            logger.debug(f"✅ Found payment: {payment_id}")
            return result.data[0]
        else:
            logger.warning(f"⚠️ Payment not found: {payment_id}")
            return None
            
    except Exception as e:
        logger.error(f"❌ get_payment_by_payment_id error: {e}")
        return None


def get_payment_by_checkout_request_id(checkout_request_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a payment by its checkout_request_id from Safaricom.
    
    Args:
        checkout_request_id: The CheckoutRequestID from Safaricom
        
    Returns:
        Payment record or None if not found
    """
    try:
        client = get_supabase_client()
        
        result = (
            client.table("payments")
            .select("*")
            .eq("checkout_request_id", checkout_request_id)
            .limit(1)
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            logger.info(f"✅ Found payment by checkout_request_id: {checkout_request_id}")
            return result.data[0]
        else:
            logger.warning(f"⚠️ Payment not found by checkout_request_id: {checkout_request_id}")
            return None
            
    except Exception as e:
        logger.error(f"❌ get_payment_by_checkout_request_id error: {e}")
        return None


def update_payment_status(payment_id: str, update_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Update a payment's status and details.
    
    Args:
        payment_id: The payment ID to update
        update_data: Dictionary with fields to update
        
    Returns:
        Updated payment record or None if failed
    """
    try:
        client = get_supabase_client()
        
        # Ensure updated_at is set
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"💾 Updating payment: {payment_id} → {update_data.get('status', 'unknown')}")
        logger.debug(f"Update data: {update_data}")
        
        result = (
            client.table("payments")
            .update(update_data)
            .eq("payment_id", payment_id)
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            logger.info(f"✅ Payment updated: {payment_id}")
            return result.data
        else:
            logger.warning(f"⚠️ No rows updated for payment: {payment_id}")
            return None
            
    except Exception as e:
        logger.error(f"❌ update_payment_status error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_payment_status(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get payment status by payment_id.
    
    Args:
        payment_id: The payment ID
        
    Returns:
        Payment record or None if not found
    """
    return get_payment_by_payment_id(payment_id)


# ─── Additional Helper Functions ──────────────────────────

def get_user_payments(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get all payments for a user.
    
    Args:
        user_id: The user ID
        limit: Maximum number of records to return
        
    Returns:
        List of payment records
    """
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
        
        return result.data if result.data else []
        
    except Exception as e:
        logger.error(f"❌ get_user_payments error: {e}")
        return []


def get_all_payments(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get all payments (admin function).
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List of payment records
    """
    try:
        client = get_supabase_client()
        
        result = (
            client.table("payments")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        return result.data if result.data else []
        
    except Exception as e:
        logger.error(f"❌ get_all_payments error: {e}")
        return []


def get_pending_payments() -> List[Dict[str, Any]]:
    """
    Get all pending payments.
    
    Returns:
        List of pending payment records
    """
    try:
        client = get_supabase_client()
        
        result = (
            client.table("payments")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=True)
            .execute()
        )
        
        return result.data if result.data else []
        
    except Exception as e:
        logger.error(f"❌ get_pending_payments error: {e}")
        return []


def delete_payment(payment_id: str) -> bool:
    """
    Delete a payment record (admin function).
    
    Args:
        payment_id: The payment ID to delete
        
    Returns:
        True if deleted, False otherwise
    """
    try:
        client = get_supabase_client()
        
        result = (
            client.table("payments")
            .delete()
            .eq("payment_id", payment_id)
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            logger.info(f"✅ Payment deleted: {payment_id}")
            return True
        else:
            logger.warning(f"⚠️ No payment deleted: {payment_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ delete_payment error: {e}")
        return False


# ─── Table Verification ────────────────────────────────────

def verify_payments_table() -> Dict[str, Any]:
    """
    Verify that the payments table exists with the correct schema.
    
    Returns:
        Dictionary with verification results
    """
    try:
        client = get_supabase_client()
        
        # Try to select one row to verify table exists
        result = (
            client.table("payments")
            .select("*")
            .limit(1)
            .execute()
        )
        
        # Check if we have the expected columns in the first row
        expected_columns = [
            "payment_id", "status", "phone", "amount", 
            "checkout_request_id", "merchant_request_id",
            "mpesa_receipt", "transaction_date", "created_at", "updated_at"
        ]
        
        if result.data and len(result.data) > 0:
            sample = result.data[0]
            existing_columns = list(sample.keys())
            
            missing_columns = [col for col in expected_columns if col not in existing_columns]
            
            return {
                "exists": True,
                "has_data": True,
                "columns": existing_columns,
                "missing_columns": missing_columns,
                "sample": sample
            }
        else:
            # Table exists but has no data
            return {
                "exists": True,
                "has_data": False,
                "message": "Table exists but has no data"
            }
            
    except Exception as e:
        logger.error(f"❌ verify_payments_table error: {e}")
        return {
            "exists": False,
            "error": str(e)
        }


# ─── Initialization ────────────────────────────────────────

# Log versions when module loads
log_supabase_version()
