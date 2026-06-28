# services/fraud_service.py – Fraud Scoring Engine

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

class FraudService:
    """Fraud detection and scoring engine."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    def calculate_fraud_score(
        self,
        user_id: str,
        phone: str,
        amount: float,
        payment_id: str = None
    ) -> Tuple[float, List[str]]:
        """
        Calculate fraud score (0-100) and return flags.
        
        Returns:
            (score, flags_list)
        """
        score = 0.0
        flags = []
        
        # 1. Check for rapid consecutive payments (velocity check)
        velocity_score, velocity_flags = self._check_velocity(user_id)
        score += velocity_score
        flags.extend(velocity_flags)
        
        # 2. Check for amount anomalies
        amount_score, amount_flags = self._check_amount_anomaly(user_id, amount)
        score += amount_score
        flags.extend(amount_flags)
        
        # 3. Check for phone number anomalies
        phone_score, phone_flags = self._check_phone_anomaly(phone)
        score += phone_score
        flags.extend(phone_flags)
        
        # 4. Check for suspicious time
        time_score, time_flags = self._check_time_anomaly()
        score += time_score
        flags.extend(time_flags)
        
        # Normalize score to 0-100
        score = min(100, max(0, score))
        
        # Log fraud check
        self._log_fraud_check(user_id, payment_id, score, flags)
        
        return score, flags
    
    def _check_velocity(self, user_id: str) -> Tuple[float, List[str]]:
        """Check for rapid consecutive payments."""
        flags = []
        score = 0.0
        
        # Get payments in last 5 minutes
        cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
        
        response = self.supabase.table('payments')\
            .select('count')\
            .eq('user_id', user_id)\
            .gt('created_at', cutoff)\
            .execute()
        
        count = response.count if response else 0
        
        if count >= 5:
            score += 30
            flags.append("RAPID_CONSECUTIVE_PAYMENTS")
        elif count >= 3:
            score += 15
            flags.append("MULTIPLE_PAYMENTS_SHORT_TIME")
        
        return score, flags
    
    def _check_amount_anomaly(self, user_id: str, amount: float) -> Tuple[float, List[str]]:
        """Check for unusual amounts."""
        flags = []
        score = 0.0
        
        # Get user's average payment
        response = self.supabase.table('payments')\
            .select('amount')\
            .eq('user_id', user_id)\
            .eq('status', 'completed')\
            .execute()
        
        if response.data and len(response.data) > 0:
            amounts = [p['amount'] for p in response.data]
            avg_amount = sum(amounts) / len(amounts)
            
            if amount > avg_amount * 3:
                score += 20
                flags.append("AMOUNT_ABOVE_USUAL")
            elif amount > avg_amount * 2:
                score += 10
                flags.append("AMOUNT_ABOVE_AVERAGE")
        
        # Check for round numbers
        if amount == int(amount) and amount > 1000:
            flags.append("ROUND_AMOUNT")
        
        # Check for very small amounts (potential test)
        if amount < 10:
            score += 10
            flags.append("VERY_SMALL_AMOUNT")
        
        return score, flags
    
    def _check_phone_anomaly(self, phone: str) -> Tuple[float, List[str]]:
        """Check for suspicious phone numbers."""
        flags = []
        score = 0.0
        
        # Check for obvious test numbers
        test_numbers = ['254712345678', '254700000000', '254711111111']
        if phone in test_numbers:
            score += 25
            flags.append("TEST_PHONE_NUMBER")
        
        # Check for repeated digits
        if len(set(phone)) <= 3:
            score += 20
            flags.append("REPEATED_DIGITS")
        
        return score, flags
    
    def _check_time_anomaly(self) -> Tuple[float, List[str]]:
        """Check for unusual time of day."""
        now = datetime.now()
        hour = now.hour
        
        # Late night payments (2am - 5am)
        if 2 <= hour <= 5:
            return 15, ["LATE_NIGHT_PAYMENT"]
        
        return 0, []
    
    def _log_fraud_check(
        self,
        user_id: str,
        payment_id: str,
        score: float,
        flags: List[str]
    ):
        """Log fraud check results."""
        try:
            data = {
                'user_id': user_id,
                'payment_id': payment_id,
                'fraud_score': score,
                'flags': flags,
                'reason': f"Score: {score}, Flags: {', '.join(flags)}" if flags else "No flags",
                'created_at': datetime.now().isoformat()
            }
            
            self.supabase.table('fraud_logs').insert(data).execute()
            logger.info(f"📊 Fraud check logged: score={score}, flags={flags}")
            
        except Exception as e:
            logger.error(f"Failed to log fraud check: {e}")
    
    def is_fraudulent(self, score: float, threshold: float = 70.0) -> bool:
        """Check if fraud score exceeds threshold."""
        return score >= threshold
