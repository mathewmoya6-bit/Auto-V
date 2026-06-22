# services/supabase_client.py - Supabase Client (Production Ready)

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# ─── Import Supabase with version handling ──────────────────────
try:
    from supabase import create_client, Client
except ImportError:
    # Fallback for older versions
    from supabase_py import create_client, Client

logger = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable is not set")
if not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_ANON_KEY environment variable is not set")

# ─── Global Clients ─────────────────────────────────────────────

_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


# ─── Main Client ──────────────────────────────────────────────

def get_supabase_client() -> Client:
    """
    Get Supabase client instance (singleton pattern).
    
    Returns:
        Client: Supabase client instance
        
    Raises:
        Exception: If client initialization fails
    """
    global _supabase_client
    
    if _supabase_client is None:
        logger.info(f"🔌 Initializing Supabase client for: {SUPABASE_URL}")
        try:
            # Try the modern way first
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        except TypeError as e:
            if 'proxy' in str(e):
                # Older version - try without proxy
                logger.warning("⚠️ Older Supabase version detected, using compatibility mode")
                try:
                    _supabase_client = create_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_ANON_KEY)
                except:
                    # Fallback: try positional arguments only
                    _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            else:
                raise
        logger.info("✅ Supabase client initialized successfully")
    
    return _supabase_client


def get_supabase() -> Client:
    """Alias for get_supabase_client()."""
    return get_supabase_client()


def get_supabase_admin_client() -> Optional[Client]:
    """
    Get Supabase admin client with service role.
    
    Returns:
        Optional[Client]: Admin client instance or None
    """
    global _supabase_admin_client
    
    if _supabase_admin_client is None and SUPABASE_KEY:
        logger.info("🔌 Initializing Supabase admin client")
        try:
            _supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except TypeError as e:
            if 'proxy' in str(e):
                logger.warning("⚠️ Older Supabase version detected, using compatibility mode")
                try:
                    _supabase_admin_client = create_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)
                except:
                    _supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            else:
                raise
        logger.info("✅ Supabase admin client initialized")
    
    return _supabase_admin_client


def reset_clients() -> None:
    """Reset all Supabase clients (useful for testing)."""
    global _supabase_client, _supabase_admin_client
    _supabase_client = None
    _supabase_admin_client = None
    logger.info("🔄 Supabase clients reset")


# ─── Health Check ─────────────────────────────────────────────

def check_health() -> Dict[str, Any]:
    """
    Check Supabase connection health.
    
    Returns:
        Dict with health status
    """
    try:
        client = get_supabase_client()
        response = client.table('system_settings').select('*').limit(1).execute()
        return {
            'connected': True,
            'message': 'Supabase connection successful',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Supabase health check failed: {str(e)}")
        return {
            'connected': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


# ─── Payment CRUD Operations ──────────────────────────────────

def create_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new payment record.
    
    Args:
        payment_data: Payment data dictionary
        
    Returns:
        Dict with success status and payment data
    """
    try:
        client = get_supabase_client()
        
        if 'amount' not in payment_data:
            return {'success': False, 'error': 'Amount is required'}
        
        # Handle payment_id if provided
        if 'payment_id' in payment_data and 'id' not in payment_data:
            pass
        
        payment_data['status'] = payment_data.get('status', 'pending')
        payment_data['payment_method'] = payment_data.get('payment_method', 'mpesa')
        payment_data['created_at'] = payment_data.get('created_at', datetime.now().isoformat())
        payment_data['updated_at'] = datetime.now().isoformat()
        
        # If 'id' is a custom string like 'PAY-XXXX', move it to payment_id
        if 'id' in payment_data and payment_data['id'] and len(payment_data['id']) > 36:
            if 'payment_id' not in payment_data:
                payment_data['payment_id'] = payment_data['id']
            del payment_data['id']
        
        response = client.table('payments').insert(payment_data).execute()
        
        if response.data:
            logger.info(f"✅ Payment created: {response.data[0].get('id')}")
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Failed to create payment'}
        
    except Exception as e:
        logger.error(f"Create payment error: {str(e)}")
        return {'success': False, 'error': str(e)}


def get_payment_by_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get payment by UUID ID.
    
    Args:
        payment_id: UUID payment ID
        
    Returns:
        Payment record or None
    """
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('id', payment_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get payment by ID error: {str(e)}")
        return None


def get_payment_by_custom_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get payment by custom payment_id (string like 'PAY-XXXXXX').
    
    Args:
        payment_id: Custom payment ID string
        
    Returns:
        Payment record or None
    """
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('payment_id', payment_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get payment by custom ID error: {str(e)}")
        return None


def get_payment_by_checkout_id(checkout_request_id: str) -> Optional[Dict[str, Any]]:
    """
    Get payment by checkout request ID.
    
    Args:
        checkout_request_id: M-Pesa checkout request ID
        
    Returns:
        Payment record or None
    """
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('checkout_request_id', checkout_request_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get payment by checkout ID error: {str(e)}")
        return None


def get_payment_by_mpesa_code(mpesa_code: str) -> Optional[Dict[str, Any]]:
    """
    Get payment by M-Pesa receipt code.
    
    Args:
        mpesa_code: M-Pesa receipt number
        
    Returns:
        Payment record or None
    """
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('mpesa_code', mpesa_code).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get payment by M-Pesa code error: {str(e)}")
        return None


def update_payment(payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a payment record by UUID ID.
    
    Args:
        payment_id: UUID payment ID
        update_data: Data to update
        
    Returns:
        Dict with success status and payment data
    """
    try:
        client = get_supabase_client()
        update_data['updated_at'] = datetime.now().isoformat()
        
        response = client.table('payments').update(update_data).eq('id', payment_id).execute()
        
        if response.data:
            logger.info(f"✅ Payment updated: {payment_id}")
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Payment not found'}
        
    except Exception as e:
        logger.error(f"Update payment error: {str(e)}")
        return {'success': False, 'error': str(e)}


def update_payment_by_custom_id(payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a payment record by custom payment_id (string).
    
    Args:
        payment_id: Custom payment ID string
        update_data: Data to update
        
    Returns:
        Dict with success status and payment data
    """
    try:
        client = get_supabase_client()
        update_data['updated_at'] = datetime.now().isoformat()
        
        response = client.table('payments').update(update_data).eq('payment_id', payment_id).execute()
        
        if response.data:
            logger.info(f"✅ Payment updated by custom ID: {payment_id}")
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Payment not found'}
        
    except Exception as e:
        logger.error(f"Update payment by custom ID error: {str(e)}")
        return {'success': False, 'error': str(e)}


def update_payment_by_checkout_id(checkout_request_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update payment by checkout request ID.
    
    Args:
        checkout_request_id: M-Pesa checkout request ID
        update_data: Data to update
        
    Returns:
        Dict with success status and payment data
    """
    try:
        client = get_supabase_client()
        update_data['updated_at'] = datetime.now().isoformat()
        
        response = client.table('payments').update(update_data).eq('checkout_request_id', checkout_request_id).execute()
        
        if response.data:
            logger.info(f"✅ Payment updated by checkout ID: {checkout_request_id}")
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Payment not found'}
        
    except Exception as e:
        logger.error(f"Update payment by checkout ID error: {str(e)}")
        return {'success': False, 'error': str(e)}


def update_payment_status(payment_id: str, status: str, extra_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Update payment status by UUID ID.
    
    Args:
        payment_id: UUID payment ID
        status: New status (pending, processing, completed, failed, cancelled)
        extra_data: Additional data to update
        
    Returns:
        Dict with success status and payment data
    """
    try:
        client = get_supabase_client()
        
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        
        if status == 'completed':
            update_data['paid_at'] = datetime.now().isoformat()
        
        if extra_data:
            update_data.update(extra_data)
        
        response = client.table('payments').update(update_data).eq('id', payment_id).execute()
        
        if response.data:
            logger.info(f"✅ Payment status updated: {payment_id} → {status}")
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Payment not found'}
        
    except Exception as e:
        logger.error(f"Update payment status error: {str(e)}")
        return {'success': False, 'error': str(e)}


def update_payment_status_by_custom_id(payment_id: str, status: str, extra_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Update payment status by custom payment_id (string).
    
    Args:
        payment_id: Custom payment ID string
        status: New status (pending, processing, completed, failed, cancelled)
        extra_data: Additional data to update
        
    Returns:
        Dict with success status and payment data
    """
    try:
        client = get_supabase_client()
        
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        
        if status == 'completed':
            update_data['paid_at'] = datetime.now().isoformat()
        
        if extra_data:
            update_data.update(extra_data)
        
        response = client.table('payments').update(update_data).eq('payment_id', payment_id).execute()
        
        if response.data:
            logger.info(f"✅ Payment status updated by custom ID: {payment_id} → {status}")
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Payment not found'}
        
    except Exception as e:
        logger.error(f"Update payment status by custom ID error: {str(e)}")
        return {'success': False, 'error': str(e)}


def update_payment_with_transaction(payment_id: str, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update payment with M-Pesa transaction data.
    
    Args:
        payment_id: UUID payment ID
        transaction_data: Transaction data (mpesa_code, receipt, etc.)
        
    Returns:
        Dict with success status and payment data
    """
    try:
        client = get_supabase_client()
        
        update_data = {
            'status': 'completed',
            'mpesa_code': transaction_data.get('mpesa_code'),
            'transaction_id': transaction_data.get('mpesa_code'),
            'mpesa_result_code': '0',
            'mpesa_result_desc': 'Transaction completed',
            'paid_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        if transaction_data.get('amount'):
            update_data['amount'] = transaction_data.get('amount')
        if transaction_data.get('phone'):
            update_data['mpesa_phone'] = transaction_data.get('phone')
        
        response = client.table('payments').update(update_data).eq('id', payment_id).execute()
        
        if response.data:
            logger.info(f"✅ Payment transaction updated: {payment_id}")
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Payment not found'}
        
    except Exception as e:
        logger.error(f"Update payment with transaction error: {str(e)}")
        return {'success': False, 'error': str(e)}


# ─── Query Functions ──────────────────────────────────────────

def get_user_payments(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get all payments for a user.
    
    Args:
        user_id: User ID
        limit: Maximum number of records
        
    Returns:
        List of payment records
    """
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get user payments error: {str(e)}")
        return []


def get_payments_by_status(status: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get payments by status.
    
    Args:
        status: Payment status
        limit: Maximum number of records
        
    Returns:
        List of payment records
    """
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('status', status).order('created_at', desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get payments by status error: {str(e)}")
        return []


def get_pending_payments(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get pending payments that need verification.
    
    Args:
        limit: Maximum number of records
        
    Returns:
        List of payment records
    """
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('status', 'pending').order('created_at', desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get pending payments error: {str(e)}")
        return []


def get_payment_stats() -> Dict[str, Any]:
    """
    Get payment statistics.
    
    Returns:
        Dict with payment statistics
    """
    try:
        client = get_supabase_client()
        
        total = client.table('payments').select('count', count='exact').execute()
        completed = client.table('payments').select('count', count='exact').eq('status', 'completed').execute()
        pending = client.table('payments').select('count', count='exact').eq('status', 'pending').execute()
        failed = client.table('payments').select('count', count='exact').eq('status', 'failed').execute()
        cancelled = client.table('payments').select('count', count='exact').eq('status', 'cancelled').execute()
        
        return {
            'total': total.count if hasattr(total, 'count') else 0,
            'completed': completed.count if hasattr(completed, 'count') else 0,
            'pending': pending.count if hasattr(pending, 'count') else 0,
            'failed': failed.count if hasattr(failed, 'count') else 0,
            'cancelled': cancelled.count if hasattr(cancelled, 'count') else 0,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get payment stats error: {str(e)}")
        return {'error': str(e)}


# ─── Delete Functions ──────────────────────────────────────────

def delete_payment(payment_id: str) -> Dict[str, Any]:
    """
    Delete a payment record by UUID ID (use with caution).
    
    Args:
        payment_id: UUID payment ID
        
    Returns:
        Dict with success status
    """
    try:
        client = get_supabase_client()
        response = client.table('payments').delete().eq('id', payment_id).execute()
        
        if response.data:
            logger.info(f"✅ Payment deleted: {payment_id}")
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Payment not found'}
    except Exception as e:
        logger.error(f"Delete payment error: {str(e)}")
        return {'success': False, 'error': str(e)}


def delete_payment_by_custom_id(payment_id: str) -> Dict[str, Any]:
    """
    Delete a payment record by custom payment_id (string).
    
    Args:
        payment_id: Custom payment ID string
        
    Returns:
        Dict with success status
    """
    try:
        client = get_supabase_client()
        response = client.table('payments').delete().eq('payment_id', payment_id).execute()
        
        if response.data:
            logger.info(f"✅ Payment deleted by custom ID: {payment_id}")
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Payment not found'}
    except Exception as e:
        logger.error(f"Delete payment by custom ID error: {str(e)}")
        return {'success': False, 'error': str(e)}


# ─── Exports ──────────────────────────────────────────────────────

__all__ = [
    # Client functions
    'get_supabase_client',
    'get_supabase',
    'get_supabase_admin_client',
    'reset_clients',
    # Health
    'check_health',
    # Create
    'create_payment',
    # Read
    'get_payment_by_id',
    'get_payment_by_custom_id',
    'get_payment_by_checkout_id',
    'get_payment_by_mpesa_code',
    # Update
    'update_payment',
    'update_payment_by_custom_id',
    'update_payment_by_checkout_id',
    'update_payment_status',
    'update_payment_status_by_custom_id',
    'update_payment_with_transaction',
    # Query
    'get_user_payments',
    'get_payments_by_status',
    'get_pending_payments',
    'get_payment_stats',
    # Delete
    'delete_payment',
    'delete_payment_by_custom_id'
]
