# services/retry_service.py – Retry Engine for Failed STK

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from db.supabase_client import get_supabase
from services.mpesa_service import initiate_stk_push
from services.payment_service import PaymentService

logger = logging.getLogger(__name__)

class RetryService:
    """Retry engine for failed STK Push attempts."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.payment_service = PaymentService()
        self.max_retries = 3
        self.retry_interval_minutes = 5
    
    def get_retryable_payments(self) -> List[Dict[str, Any]]:
        """Get payments that need retry."""
        cutoff = (datetime.now() - timedelta(minutes=self.retry_interval_minutes)).isoformat()
        
        response = self.supabase.table('payments')\
            .select('*')\
            .eq('status', 'failed')\
            .lt('retry_count', self.max_retries)\
            .lt('last_retry_at', cutoff)\
            .execute()
        
        return response.data if response.data else []
    
    def retry_payment(self, payment_id: str) -> Dict[str, Any]:
        """Retry a failed payment."""
        payment = self.payment_service.get_payment(payment_id)
        
        if not payment:
            raise Exception(f"Payment not found: {payment_id}")
        
        if payment['retry_count'] >= self.max_retries:
            raise Exception(f"Max retries exceeded for payment {payment_id}")
        
        try:
            # Increment retry count
            update_data = {
                'retry_count': payment['retry_count'] + 1,
                'last_retry_at': datetime.now().isoformat()
            }
            
            self.supabase.table('payments')\
                .update(update_data)\
                .eq('id', payment_id)\
                .execute()
            
            # Re-initiate STK Push
            mpesa_response = initiate_stk_push(
                phone=payment['phone'],
                amount=payment['amount'],
                payment_id=payment_id,
                service=payment['service_type']
            )
            
            checkout_id = mpesa_response.get('CheckoutRequestID')
            
            # Update with new checkout ID
            update_data = {
                'checkout_request_id': checkout_id,
                'status': 'processing',
                'updated_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('payments')\
                .update(update_data)\
                .eq('id', payment_id)\
                .execute()
            
            logger.info(f"🔄 Retry successful for payment {payment_id}")
            
            return result.data[0] if result.data else payment
            
        except Exception as e:
            logger.error(f"Retry failed for payment {payment_id}: {e}")
            raise
    
    def process_retries(self) -> int:
        """Process all retryable payments."""
        payments = self.get_retryable_payments()
        success_count = 0
        
        for payment in payments:
            try:
                self.retry_payment(payment['id'])
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to retry payment {payment['id']}: {e}")
        
        if success_count > 0:
            logger.info(f"🔄 Retry processed {success_count} payments")
        
        return success_count
