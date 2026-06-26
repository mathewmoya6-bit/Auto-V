"""
Payment Worker - Background Payment Processing
Handles payment retries, status updates, and cleanup tasks
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from threading import Thread, Event
from contextlib import asynccontextmanager

from app.services.retry_service import RetryService
from app.services.payment_service import PaymentService
from app.core.database import supabase

logger = logging.getLogger(__name__)


class PaymentWorker:
    """
    Background worker for payment processing.
    
    Handles:
    - Retry failed payments
    - Update pending payment status
    - Clean up expired transactions
    - Process webhook retries
    - Generate payment reports
    """
    
    def __init__(self):
        self.retry_service = RetryService()
        self.payment_service = PaymentService()
        self.running = False
        self.thread: Optional[Thread] = None
        self.stop_event = Event()
        self.last_run = None
        self.stats = {
            'retries_processed': 0,
            'status_updates': 0,
            'cleanups': 0,
            'errors': 0,
            'last_success': None
        }
    
    def start(self):
        """Start the worker in background."""
        if self.running:
            logger.warning("⚠️ Payment worker already running")
            return
        
        self.running = True
        self.stop_event.clear()
        self.thread = Thread(target=self._run, daemon=True, name="PaymentWorker")
        self.thread.start()
        logger.info("🚀 Payment worker started")
    
    def stop(self):
        """Stop the worker gracefully."""
        if not self.running:
            return
        
        self.running = False
        self.stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=10)
        
        logger.info("🛑 Payment worker stopped")
    
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self.running and self.thread and self.thread.is_alive()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            'running': self.is_running(),
            'last_run': self.last_run,
            'stats': self.stats,
            'uptime': (datetime.now() - self.last_run) if self.last_run else None
        }
    
    def _run(self):
        """Main worker loop."""
        logger.info("🔄 Payment worker loop started")
        
        while self.running and not self.stop_event.is_set():
            try:
                self.last_run = datetime.now()
                
                # Run all tasks
                self._process_retries()
                self._update_pending_status()
                self._cleanup_expired()
                self._process_webhook_retries()
                
                # Generate daily report if needed
                if self._should_generate_report():
                    self._generate_daily_report()
                
                self.stats['last_success'] = datetime.now()
                
                # Sleep for 60 seconds
                self.stop_event.wait(60)
                
            except Exception as e:
                logger.error(f"❌ Payment worker error: {e}", exc_info=True)
                self.stats['errors'] += 1
                self.stop_event.wait(60)  # Wait longer on error
    
    def _process_retries(self):
        """Process failed payment retries."""
        try:
            retry_count = self.retry_service.process_retries()
            if retry_count > 0:
                logger.info(f"📊 Processed {retry_count} retries")
                self.stats['retries_processed'] += retry_count
        except Exception as e:
            logger.error(f"Retry processing error: {e}")
    
    def _update_pending_status(self):
        """Update pending payment statuses."""
        try:
            # Get pending payments older than 5 minutes
            cutoff = datetime.now() - timedelta(minutes=5)
            
            pending_payments = supabase.table("payments") \
                .select("*") \
                .eq("status", "pending") \
                .lt("created_at", cutoff.isoformat()) \
                .execute()
            
            updated = 0
            for payment in pending_payments.data:
                try:
                    # Query M-Pesa status
                    result = self.payment_service.query_status(
                        payment.get("checkout_request_id")
                    )
                    
                    if result and result.get("status") != "pending":
                        # Update payment
                        supabase.table("payments") \
                            .update({
                                "status": result.get("status"),
                                "mpesa_result_code": result.get("result_code"),
                                "mpesa_result_desc": result.get("result_desc"),
                                "updated_at": datetime.now().isoformat()
                            }) \
                            .eq("payment_id", payment.get("payment_id")) \
                            .execute()
                        
                        updated += 1
                        
                except Exception as e:
                    logger.error(f"Failed to update payment {payment.get('payment_id')}: {e}")
            
            if updated > 0:
                logger.info(f"📊 Updated {updated} pending payments")
                self.stats['status_updates'] += updated
                
        except Exception as e:
            logger.error(f"Pending status update error: {e}")
    
    def _cleanup_expired(self):
        """Clean up expired transactions."""
        try:
            cutoff = datetime.now() - timedelta(days=30)
            
            # Archive completed payments older than 30 days
            completed = supabase.table("payments") \
                .select("*") \
                .eq("status", "completed") \
                .lt("created_at", cutoff.isoformat()) \
                .execute()
            
            archived = 0
            for payment in completed.data:
                try:
                    # Move to archive table (or mark as archived)
                    supabase.table("payments") \
                        .update({"is_archived": True}) \
                        .eq("payment_id", payment.get("payment_id")) \
                        .execute()
                    archived += 1
                except Exception as e:
                    logger.error(f"Failed to archive payment {payment.get('payment_id')}: {e}")
            
            if archived > 0:
                logger.info(f"📊 Archived {archived} old payments")
                self.stats['cleanups'] += archived
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def _process_webhook_retries(self):
        """Process webhook retries."""
        try:
            # Get failed webhook deliveries
            failed_webhooks = supabase.table("webhook_deliveries") \
                .select("*") \
                .eq("status", "failed") \
                .lt("retry_count", 5) \
                .order("created_at") \
                .limit(10) \
                .execute()
            
            processed = 0
            for webhook in failed_webhooks.data:
                try:
                    # Retry delivery
                    success = self.payment_service.retry_webhook(
                        webhook.get("webhook_id"),
                        webhook.get("payload")
                    )
                    
                    if success:
                        supabase.table("webhook_deliveries") \
                            .update({
                                "status": "delivered",
                                "retry_count": webhook.get("retry_count", 0) + 1,
                                "delivered_at": datetime.now().isoformat()
                            }) \
                            .eq("webhook_id", webhook.get("webhook_id")) \
                            .execute()
                        processed += 1
                        
                except Exception as e:
                    logger.error(f"Failed to retry webhook {webhook.get('webhook_id')}: {e}")
            
            if processed > 0:
                logger.info(f"📊 Processed {processed} webhook retries")
                
        except Exception as e:
            logger.error(f"Webhook retry error: {e}")
    
    def _should_generate_report(self) -> bool:
        """Check if daily report should be generated."""
        # Generate report once per day
        if not hasattr(self, '_last_report_date'):
            self._last_report_date = None
        
        today = datetime.now().date()
        if self._last_report_date != today:
            self._last_report_date = today
            return True
        
        return False
    
    def _generate_daily_report(self):
        """Generate daily payment report."""
        try:
            today = datetime.now().date()
            start = datetime.combine(today, datetime.min.time())
            end = datetime.combine(today, datetime.max.time())
            
            # Get today's payments
            payments = supabase.table("payments") \
                .select("*") \
                .gte("created_at", start.isoformat()) \
                .lte("created_at", end.isoformat()) \
                .execute()
            
            total_amount = 0
            completed = 0
            failed = 0
            pending = 0
            
            for payment in payments.data:
                total_amount += payment.get("amount", 0)
                status = payment.get("status")
                if status == "completed":
                    completed += 1
                elif status == "failed":
                    failed += 1
                elif status == "pending":
                    pending += 1
            
            if payments.data:
                logger.info(f"📊 Daily Report - {today}")
                logger.info(f"   Total Payments: {len(payments.data)}")
                logger.info(f"   Total Amount: KES {total_amount:,.2f}")
                logger.info(f"   Completed: {completed}")
                logger.info(f"   Failed: {failed}")
                logger.info(f"   Pending: {pending}")
                
                # Store report in database
                supabase.table("payment_reports").insert({
                    "report_date": today.isoformat(),
                    "total_payments": len(payments.data),
                    "total_amount": total_amount,
                    "completed": completed,
                    "failed": failed,
                    "pending": pending,
                    "created_at": datetime.now().isoformat()
                }).execute()
                
        except Exception as e:
            logger.error(f"Daily report generation error: {e}")


# ─── Async Version ──────────────────────────────────────────────

class AsyncPaymentWorker:
    """
    Async version of payment worker for FastAPI.
    """
    
    def __init__(self):
        self.retry_service = RetryService()
        self.payment_service = PaymentService()
        self.running = False
        self.task = None
    
    async def start(self):
        """Start the worker asynchronously."""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("🚀 Async payment worker started")
    
    async def stop(self):
        """Stop the worker gracefully."""
        self.running = False
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=10)
            except asyncio.TimeoutError:
                self.task.cancel()
        logger.info("🛑 Async payment worker stopped")
    
    async def _run(self):
        """Main async worker loop."""
        while self.running:
            try:
                # Process retries
                retry_count = await self.retry_service.process_retries_async()
                if retry_count > 0:
                    logger.info(f"📊 Processed {retry_count} retries")
                
                # Update pending statuses
                await self._update_pending_status_async()
                
                # Cleanup expired
                await self._cleanup_expired_async()
                
                # Sleep
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Async worker error: {e}")
                await asyncio.sleep(60)
    
    async def _update_pending_status_async(self):
        """Async update pending payment statuses."""
        try:
            cutoff = datetime.now() - timedelta(minutes=5)
            
            pending_payments = supabase.table("payments") \
                .select("*") \
                .eq("status", "pending") \
                .lt("created_at", cutoff.isoformat()) \
                .execute()
            
            for payment in pending_payments.data:
                try:
                    result = await self.payment_service.query_status_async(
                        payment.get("checkout_request_id")
                    )
                    
                    if result and result.get("status") != "pending":
                        supabase.table("payments") \
                            .update({
                                "status": result.get("status"),
                                "updated_at": datetime.now().isoformat()
                            }) \
                            .eq("payment_id", payment.get("payment_id")) \
                            .execute()
                except Exception as e:
                    logger.error(f"Failed to update payment: {e}")
                    
        except Exception as e:
            logger.error(f"Async status update error: {e}")
    
    async def _cleanup_expired_async(self):
        """Async cleanup expired transactions."""
        try:
            cutoff = datetime.now() - timedelta(days=30)
            
            completed = supabase.table("payments") \
                .select("*") \
                .eq("status", "completed") \
                .lt("created_at", cutoff.isoformat()) \
                .execute()
            
            for payment in completed.data:
                supabase.table("payments") \
                    .update({"is_archived": True}) \
                    .eq("payment_id", payment.get("payment_id")) \
                    .execute()
                    
        except Exception as e:
            logger.error(f"Async cleanup error: {e}")


# ─── Singleton Instance ──────────────────────────────────────────

_worker_instance: Optional[PaymentWorker] = None
_async_worker_instance: Optional[AsyncPaymentWorker] = None


def get_worker() -> PaymentWorker:
    """Get payment worker instance (singleton)."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = PaymentWorker()
    return _worker_instance


def get_async_worker() -> AsyncPaymentWorker:
    """Get async payment worker instance (singleton)."""
    global _async_worker_instance
    if _async_worker_instance is None:
        _async_worker_instance = AsyncPaymentWorker()
    return _async_worker_instance


# ─── Context Manager ────────────────────────────────────────────

@asynccontextmanager
async def worker_context():
    """Async context manager for payment worker."""
    worker = get_async_worker()
    await worker.start()
    try:
        yield worker
    finally:
        await worker.stop()


# ─── Exports ────────────────────────────────────────────────────

__all__ = [
    'PaymentWorker',
    'AsyncPaymentWorker',
    'get_worker',
    'get_async_worker',
    'worker_context',
]
