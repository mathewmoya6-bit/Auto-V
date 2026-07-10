from typing import Optional, Dict, Any
from datetime import datetime
import random
import string
from app.core.config import settings
from app.core.database import supabase


class PaymentService:
    def __init__(self):
        self.mpesa_consumer_key = settings.mpesa_consumer_key
        self.mpesa_consumer_secret = settings.mpesa_consumer_secret
        self.mpesa_passkey = settings.mpesa_passkey
        self.mpesa_shortcode = settings.mpesa_shortcode
        self.mpesa_environment = settings.mpesa_environment
    
    async def initiate_payment(self, user_id: str, amount: float, phone_number: str, description: str = "") -> Dict[str, Any]:
        """Initiate M-Pesa payment"""
        # Generate unique transaction ID
        transaction_id = self._generate_transaction_id()
        
        # Create payment record
        payment_data = {
            "user_id": user_id,
            "amount": amount,
            "phone_number": phone_number,
            "description": description,
            "transaction_id": transaction_id,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        result = (
            supabase
            .table("payments")
            .insert(payment_data)
            .execute()
        )
        
        # In production, integrate with M-Pesa API here
        # For now, simulate successful payment
        payment_response = {
            "payment_id": result.data[0]["id"],
            "transaction_id": transaction_id,
            "status": "pending",
            "amount": amount,
            "phone_number": phone_number,
            "message": "Payment initiated successfully"
        }
        
        return payment_response
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status"""
        result = (
            supabase
            .table("payments")
            .select("*")
            .eq("id", payment_id)
            .execute()
        )
        
        if not result.data:
            raise ValueError("Payment not found")
        
        payment = result.data[0]
        
        # In production, check with M-Pesa API for actual status
        return {
            "payment_id": payment["id"],
            "transaction_id": payment["transaction_id"],
            "status": payment["status"],
            "amount": payment["amount"],
            "phone_number": payment["phone_number"],
            "completed_at": payment.get("completed_at")
        }
    
    async def get_payment_history(self, user_id: str, limit: int = 50) -> list:
        """Get user's payment history"""
        result = (
            supabase
            .table("payments")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        return result.data
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"PAY{timestamp}{random_str}"
    
    async def simulate_payment_completion(self, payment_id: str) -> Dict[str, Any]:
        """Simulate payment completion (for testing only)"""
        payment = (
            supabase
            .table("payments")
            .select("*")
            .eq("id", payment_id)
            .execute()
        )
        
        if not payment.data:
            raise ValueError("Payment not found")
        
        update_data = {
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }
        
        result = (
            supabase
            .table("payments")
            .update(update_data)
            .eq("id", payment_id)
            .execute()
        )
        
        return result.data[0]
