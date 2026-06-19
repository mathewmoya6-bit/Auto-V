# workers/payment_worker.py – Background Payment Worker

import logging
import time
import threading
from datetime import datetime
from services.retry_service import RetryService
from services.payment_service import PaymentService

logger = logging.getLogger(__name__)

class PaymentWorker:
    """Background worker for payment processing."""
    
    def __init__(self):
        self.retry_service = RetryService()
        self.payment_service = PaymentService()
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the worker in background."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("🚀 Payment worker started")
    
    def stop(self):
        """Stop the worker."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 Payment worker stopped")
    
    def _run(self):
        """Main worker loop."""
        while self.running:
            try:
                # Process retries
                retry_count = self.retry_service.process_retries()
                
                if retry_count > 0:
                    logger.info(f"📊 Processed {retry_count} retries")
                
                # Sleep for 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(60)
