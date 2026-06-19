# services/payment_service.py – Payment State Machine

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from db.supabase_client import get_supabase
from services.mpesa_service import initiate_stk_push, query_payment_status
from services.fraud_service import calculate_fraud_score
from services.invoice_service import generate_invoice
from utils.phone_utils import normalize_phone

logger = logging.getLogger(__name__)

class PaymentStatus(Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'

class PaymentService:
    """Payment state machine and business logic."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    def create_payment(
        self,
        user_id: str,
        phone: str,
        amount: float,
        service_type: str,
        purpose: str = None
    ) -> Dict[str, Any]:
        """
        Create a new payment record.
        
        Returns:
            Payment record with status 'pending'
        """
        # Normalize phone
        phone = normalize_phone(phone)
        
        # Generate reference
        reference = f'AUTO-{uuid.uuid4().hex[:8].upper()}'
        
        payment_data = {
            'user_id': user_id,
            'phone': phone,
            'amount': amount,
            'service_type': service_type,
            'purpose': purpose,
            'status': PaymentStatus.PENDING.value,
            'reference': reference,
            'created_at': datetime.now().isoformat()
        }
        
        response = self.supabase.table('payments').insert(payment_data).execute()
        
        if not response.data:
            raise Exception("Failed to create payment record")
        
        payment = response.data[0]
        logger.info(f"✅ Payment created: {payment['id']} for user {user_id}")
        
        return payment
    
    def initiate(self, payment_id: str) -> Dict[str, Any]:
        """
        Initiate STK Push for a payment.
        
        Returns:
            Payment record with checkout_request_id
        """
        # Get payment
        payment = self.get_payment(payment_id)
        
        if not payment:
            raise Exception(f"Payment not found: {payment_id}")
        
        if payment['status'] != PaymentStatus.PENDING.value:
            raise Exception(f"Payment is already {payment['status']}")
        
        try:
            # Initiate STK Push
            mpesa_response = initiate_stk_push(
                phone=payment['phone'],
                amount=payment['amount'],
                payment_id=payment_id,
                service=payment['service_type']
            )
            
            checkout_id = mpesa_response.get('CheckoutRequestID')
            
            # Update payment with checkout ID
            update_data = {
                'checkout_request_id': checkout_id,
                'status': PaymentStatus.PROCESSING.value,
                'updated_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('payments')\
                .update(update_data)\
                .eq('id', payment_id)\
                .execute()
            
            logger.info(f"✅ STK Push initiated for payment {payment_id}")
            
            return result.data[0] if result.data else payment
            
        except Exception as e:
            # Mark as failed
            self.fail_payment(payment_id, str(e))
            raise
    
    def process_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process M-Pesa callback with deduplication.
        
        Returns:
            Updated payment record
        """
        stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
        
        if not stk_callback:
            raise Exception("Invalid callback structure")
        
        checkout_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        transaction_id = stk_callback.get('TransactionID')
        
        if not checkout_id:
            raise Exception("Missing CheckoutRequestID")
        
        # Find payment
        response = self.supabase.table('payments')\
            .select('*')\
            .eq('checkout_request_id', checkout_id)\
            .execute()
        
        if not response.data:
            raise Exception(f"Payment not found for checkout: {checkout_id}")
        
        payment = response.data[0]
        payment_id = payment['id']
        
        # Idempotency check
        if payment['status'] == PaymentStatus.COMPLETED.value:
            logger.info(f"Payment {payment_id} already completed, skipping duplicate callback")
            return payment
        
        # Process result
        if str(result_code) == '0':
            return self.complete_payment(payment_id, transaction_id, result_code, result_desc)
        else:
            return self.fail_payment(payment_id, result_desc, result_code)
    
    def complete_payment(
        self,
        payment_id: str,
        transaction_id: str = None,
        result_code: str = '0',
        result_desc: str = 'Success'
    ) -> Dict[str, Any]:
        """Mark payment as completed."""
        update_data = {
            'status': PaymentStatus.COMPLETED.value,
            'transaction_id': transaction_id,
            'mpesa_result_code': result_code,
            'mpesa_result_desc': result_desc,
            'completed_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        result = self.supabase.table('payments')\
            .update(update_data)\
            .eq('id', payment_id)\
            .execute()
        
        if result.data:
            payment = result.data[0]
            logger.info(f"✅ Payment {payment_id} completed")
            
            # Generate invoice
            try:
                generate_invoice(payment_id)
            except Exception as e:
                logger.error(f"Failed to generate invoice: {e}")
            
            return payment
        
        raise Exception(f"Failed to complete payment: {payment_id}")
    
    def fail_payment(
        self,
        payment_id: str,
        reason: str,
        result_code: str = None
    ) -> Dict[str, Any]:
        """Mark payment as failed."""
        update_data = {
            'status': PaymentStatus.FAILED.value,
            'mpesa_result_desc': reason,
            'mpesa_result_code': result_code,
            'updated_at': datetime.now().isoformat()
        }
        
        result = self.supabase.table('payments')\
            .update(update_data)\
            .eq('id', payment_id)\
            .execute()
        
        if result.data:
            logger.warning(f"❌ Payment {payment_id} failed: {reason}")
            return result.data[0]
        
        raise Exception(f"Failed to mark payment as failed: {payment_id}")
    
    def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment by ID."""
        response = self.supabase.table('payments')\
            .select('*')\
            .eq('id', payment_id)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_payment_by_checkout_id(self, checkout_id: str) -> Optional[Dict[str, Any]]:
        """Get payment by checkout request ID."""
        response = self.supabase.table('payments')\
            .select('*')\
            .eq('checkout_request_id', checkout_id)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_user_payments(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all payments for a user."""
        response = self.supabase.table('payments')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return response.data if response.data else []
