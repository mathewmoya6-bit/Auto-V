# ============================================================
# services/supabase_client.py - Supabase Client Wrapper
# ============================================================

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

_supabase_client = None


def get_supabase_client():
    """Get Supabase client instance (singleton) - handles proxy parameter issue."""
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    try:
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        
        logger.info(f"🔗 Connecting to Supabase: {SUPABASE_URL}")
        
        # Try different initialization methods
        try:
            # Method 1: Use supabase-py (older version that works)
            from supabase_py import create_client
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            logger.info("✅ Supabase client initialized (supabase-py method)")
            
        except ImportError:
            try:
                # Method 2: Use supabase with create_client
                from supabase import create_client
                _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
                logger.info("✅ Supabase client initialized (standard method)")
                
            except TypeError as e:
                if "proxy" in str(e):
                    logger.warning("⚠️ Proxy parameter issue, using direct Client initialization...")
                    # Method 3: Direct Client import (bypasses proxy)
                    from supabase.client import Client
                    _supabase_client = Client(SUPABASE_URL, SUPABASE_ANON_KEY)
                    logger.info("✅ Supabase client initialized (direct Client method)")
                else:
                    raise
            except ImportError:
                # Method 4: Try from supabase.lib.client
                try:
                    from supabase.lib.client import Client
                    _supabase_client = Client(SUPABASE_URL, SUPABASE_ANON_KEY)
                    logger.info("✅ Supabase client initialized (lib.client method)")
                except ImportError:
                    raise ImportError("Could not import Supabase client. Please install supabase-py or supabase package.")
        
        # Verify the client works
        try:
            test_result = (
                _supabase_client.table("payments")
                .select("payment_id")
                .limit(1)
                .execute()
            )
            logger.info("✅ Supabase connection verified")
        except Exception as test_e:
            logger.warning(f"⚠️ Test query failed, but client created: {test_e}")
        
        return _supabase_client
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
        import traceback
        traceback.print_exc()
        raise


# ─── Payment CRUD Operations ──────────────────────────────

def create_payment(payment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new payment record in Supabase."""
    try:
        client = get_supabase_client()
        
        if "created_at" not in payment_data:
            payment_data["created_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"💾 Creating payment: {payment_data.get('payment_id')}")
        
        result = client.table("payments").insert(payment_data).execute()
        
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
    """Get a payment by its payment_id."""
    try:
        client = get_supabase_client()
        
        result = client.table("payments").select("*").eq("payment_id", payment_id).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        else:
            logger.warning(f"⚠️ Payment not found: {payment_id}")
            return None
            
    except Exception as e:
        logger.error(f"❌ get_payment_by_payment_id error: {e}")
        return None


def get_payment_by_checkout_request_id(checkout_request_id: str) -> Optional[Dict[str, Any]]:
    """Get a payment by its checkout_request_id from Safaricom."""
    try:
        client = get_supabase_client()
        
        result = client.table("payments").select("*").eq("checkout_request_id", checkout_request_id).limit(1).execute()
        
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
    """Update a payment's status and details."""
    try:
        client = get_supabase_client()
        
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"💾 Updating payment: {payment_id} → {update_data.get('status', 'unknown')}")
        
        result = client.table("payments").update(update_data).eq("payment_id", payment_id).execute()
        
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
    """Get payment status by payment_id."""
    return get_payment_by_payment_id(payment_id)


def get_user_payments(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all payments for a user."""
    try:
        client = get_supabase_client()
        
        result = client.table("payments").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        logger.error(f"❌ get_user_payments error: {e}")
        return []


def get_all_payments(limit: int = 100) -> List[Dict[str, Any]]:
    """Get all payments (admin function)."""
    try:
        client = get_supabase_client()
        
        result = client.table("payments").select("*").order("created_at", desc=True).limit(limit).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        logger.error(f"❌ get_all_payments error: {e}")
        return []


def get_pending_payments() -> List[Dict[str, Any]]:
    """Get all pending payments."""
    try:
        client = get_supabase_client()
        
        result = client.table("payments").select("*").eq("status", "pending").order("created_at", desc=True).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        logger.error(f"❌ get_pending_payments error: {e}")
        return []


def delete_payment(payment_id: str) -> bool:
    """Delete a payment record (admin function)."""
    try:
        client = get_supabase_client()
        
        result = client.table("payments").delete().eq("payment_id", payment_id).execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"✅ Payment deleted: {payment_id}")
            return True
        else:
            logger.warning(f"⚠️ No payment deleted: {payment_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ delete_payment error: {e}")
        return False
