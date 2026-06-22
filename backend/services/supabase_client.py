# services/supabase_client.py - Production Ready v3

import os
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable is not set")
if not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_ANON_KEY environment variable is not set")

_supabase_client = None


# ─── Client ─────────────────────────────────────────────────────

def get_supabase_client() -> Client:
    """Get Supabase client instance (singleton)."""
    global _supabase_client
    
    if _supabase_client is None:
        logger.info(f"🔌 Initializing Supabase client")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("✅ Supabase client initialized")
    
    return _supabase_client


# ─── Payment CRUD Operations ──────────────────────────────────

def create_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new payment record with UUID and payment_id."""
    try:
        client = get_supabase_client()
        
        # Validate required fields
        if 'amount' not in payment_data:
            return {'success': False, 'error': 'Amount is required'}
        
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
        payment_data['status'] = payment_data.get('status', 'pending')
        payment_data['payment_method'] = payment_data.get('payment_method', 'mpesa')
        payment_data['created_at'] = payment_data.get('created_at', datetime.now().isoformat())
        payment_data['updated_at'] = datetime.now().isoformat()
        
        logger.info(f"📝 Creating payment: {payment_data['payment_id']}")
        
        # Insert into database
        response = client.table('payments').insert(payment_data).execute()
        
        if response.data:
            logger.info(f"✅ Payment created: {response.data[0].get('payment_id')}")
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Failed to create payment'}
        
    except Exception as e:
        logger.error(f"Create payment error: {str(e)}")
        return {'success': False, 'error': str(e)}


def get_payment_by_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by UUID ID."""
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('id', payment_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get payment by ID error: {str(e)}")
        return None


def get_payment_by_custom_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by custom payment_id (string like 'PAY-XXXXXX')."""
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('payment_id', payment_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get payment by custom ID error: {str(e)}")
        return None


def get_payment_by_checkout_id(checkout_request_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by checkout request ID."""
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('checkout_request_id', checkout_request_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get payment by checkout ID error: {str(e)}")
        return None


def get_payment_by_mpesa_code(mpesa_code: str) -> Optional[Dict[str, Any]]:
    """Get payment by M-Pesa receipt code."""
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('mpesa_code', mpesa_code).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get payment by M-Pesa code error: {str(e)}")
        return None


def update_payment(payment_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a payment record by UUID ID."""
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
    """Update a payment record by custom payment_id (string)."""
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


def update_payment_status(payment_id: str, status: str, extra_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Update payment status by UUID ID."""
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


def get_user_payments(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all payments for a user."""
    try:
        client = get_supabase_client()
        response = client.table('payments').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get user payments error: {str(e)}")
        return []


__all__ = [
    'get_supabase_client',
    'create_payment',
    'get_payment_by_id',
    'get_payment_by_custom_id',
    'get_payment_by_checkout_id',
    'get_payment_by_mpesa_code',
    'update_payment',
    'update_payment_by_custom_id',
    'update_payment_status',
    'get_user_payments'
]
