# services/invoice_service.py – Invoice Generator

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

def generate_invoice(payment_id: str) -> Dict[str, Any]:
    """
    Generate invoice for a completed payment.
    
    Args:
        payment_id: Payment ID
    
    Returns:
        Invoice record
    """
    supabase = get_supabase()
    
    # Get payment
    response = supabase.table('payments')\
        .select('*')\
        .eq('id', payment_id)\
        .execute()
    
    if not response.data:
        raise Exception(f"Payment not found: {payment_id}")
    
    payment = response.data[0]
    
    # Check if invoice already exists
    existing = supabase.table('invoices')\
        .select('*')\
        .eq('payment_id', payment_id)\
        .execute()
    
    if existing.data:
        return existing.data[0]
    
    # Generate invoice number
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    # Calculate tax (16% VAT)
    tax = round(payment['amount'] * 0.16, 2)
    total = payment['amount'] + tax
    
    invoice_data = {
        'payment_id': payment_id,
        'invoice_number': invoice_number,
        'user_id': payment['user_id'],
        'amount': payment['amount'],
        'tax': tax,
        'total': total,
        'status': 'paid',
        'created_at': datetime.now().isoformat(),
        'paid_at': datetime.now().isoformat()
    }
    
    result = supabase.table('invoices').insert(invoice_data).execute()
    
    if not result.data:
        raise Exception(f"Failed to create invoice for payment {payment_id}")
    
    logger.info(f"📄 Invoice generated: {invoice_number}")
    
    return result.data[0]


def get_invoice(invoice_id: str) -> Optional[Dict[str, Any]]:
    """Get invoice by ID."""
    supabase = get_supabase()
    response = supabase.table('invoices')\
        .select('*')\
        .eq('id', invoice_id)\
        .execute()
    
    return response.data[0] if response.data else None


def get_invoice_by_number(invoice_number: str) -> Optional[Dict[str, Any]]:
    """Get invoice by invoice number."""
    supabase = get_supabase()
    response = supabase.table('invoices')\
        .select('*')\
        .eq('invoice_number', invoice_number)\
        .execute()
    
    return response.data[0] if response.data else None
