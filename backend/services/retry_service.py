"""
Retry Service - Handles payment retries
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.core.database import supabase

logger = logging.getLogger(__name__)


class RetryService:
    """Service for handling payment retries."""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 60  # seconds
    
    def process_retries(self) -> int:
        """
        Process failed payment retries.
        
        Returns:
            Number of retries processed
        """
        try:
            # Get failed payments to retry
            cutoff = datetime.now() - timedelta(seconds=self.retry_delay)
            
            failed_payments = supabase.table("payments") \
                .select("*") \
                .eq("status", "failed") \
                .lt("retry_count", self.max_retries) \
                .lt("updated_at", cutoff.isoformat()) \
                .execute()
            
            processed = 0
            for payment in failed_payments.data:
                try:
                    # Increment retry count
                    retry_count = payment.get("retry_count", 0) + 1
                    
                    # Retry payment
                    result = self._retry_payment(payment)
                    
                    if result:
                        supabase.table("payments") \
                            .update({
                                "status": "pending",
                                "retry_count": retry_count,
                                "retried_at": datetime.now().isoformat()
                            }) \
                            .eq("payment_id", payment.get("payment_id")) \
                            .execute()
                        processed += 1
                    else:
                        # Mark as retry failed
                        supabase.table("payments") \
                            .update({
                                "retry_count": retry_count,
                                "retried_at": datetime.now().isoformat(),
                                "retry_failed": True
                            }) \
                            .eq("payment_id", payment.get("payment_id")) \
                            .execute()
                        
                except Exception as e:
                    logger.error(f"Failed to retry payment {payment.get('payment_id')}: {e}")
            
            return processed
            
        except Exception as e:
            logger.error(f"Retry processing error: {e}")
            return 0
    
    async def process_retries_async(self) -> int:
        """Async version of process_retries."""
        # Run sync version in thread pool
        import asyncio
        return await asyncio.to_thread(self.process_retries)
    
    def _retry_payment(self, payment: Dict[str, Any]) -> bool:
        """
        Retry a failed payment.
        
        Args:
            payment: Payment record
            
        Returns:
            True if retry was successful, False otherwise
        """
        # This would call the payment service to retry
        # For now, just log and return True
        logger.info(f"🔄 Retrying payment: {payment.get('payment_id')}")
        return True


class PaymentRetryService:
    """Alternative retry service with exponential backoff."""
    
    def __init__(self):
        self.max_retries = 5
        self.base_delay = 30
        self.max_delay = 3600
    
    def calculate_delay(self, retry_count: int) -> int:
        """Calculate delay with exponential backoff."""
        delay = self.base_delay * (2 ** retry_count)
        return min(delay, self.max_delay)
    
    def should_retry(self, payment: Dict[str, Any]) -> bool:
        """Check if payment should be retried."""
        retry_count = payment.get("retry_count", 0)
        if retry_count >= self.max_retries:
            return False
        
        last_retry = payment.get("retried_at")
        if last_retry:
            delay = self.calculate_delay(retry_count)
            last_retry_time = datetime.fromisoformat(last_retry)
            if datetime.now() - last_retry_time < timedelta(seconds=delay):
                return False
        
        return True
