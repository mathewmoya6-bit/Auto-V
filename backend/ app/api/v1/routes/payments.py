# app/api/v1/routes/payments.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import base64
import hashlib
import hmac
import requests
from datetime import datetime
import uuid

from app.core.config import settings
from app.core.database import get_db
from app.core.security import JWTBearer
from app.core.logging import get_logger
from app.services.mpesa import MpesaService

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = get_logger(__name__)

class PaymentRequest(BaseModel):
    amount: float
    phone_number: str
    vehicle_id: str
    payment_type: str = "valuation"  # valuation, premium, subscription
    description: Optional[str] = None

class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    checkout_request_id: Optional[str] = None
    merchant_request_id: Optional[str] = None
    amount: float
    phone_number: str
    payment_type: str
    created_at: str

@router.post("/initiate", response_model=PaymentResponse)
async def initiate_payment(
    payment: PaymentRequest,
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """Initiate M-PESA payment"""
    try:
        user_id = request.state.user_id
        
        # Check if feature is enabled
        if not settings.FEATURE_MPESA:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment service is currently unavailable"
            )
        
        # Validate payment amount
        if payment.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment amount"
            )
        
        # Format phone number
        phone_number = payment.phone_number
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
        # Initialize M-PESA service
        mpesa = MpesaService()
        
        # Initiate STK Push
        result = await mpesa.stk_push(
            amount=payment.amount,
            phone_number=phone_number,
            account_reference=f"AUTOV-{uuid.uuid4().hex[:8].upper()}",
            transaction_desc=payment.description or f"Auto-V {payment.payment_type} payment"
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('message', 'Payment initiation failed')
            )
        
        # Create payment record
        payment_id = str(uuid.uuid4())
        payment_data = {
            'id': payment_id,
            'user_id': user_id,
            'vehicle_id': payment.vehicle_id,
            'amount': payment.amount,
            'phone_number': payment.phone_number,
            'payment_type': payment.payment_type,
            'description': payment.description,
            'status': 'pending',
            'checkout_request_id': result.get('CheckoutRequestID'),
            'merchant_request_id': result.get('MerchantRequestID'),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        db.table('payments').insert(payment_data).execute()
        
        logger.info(f"Payment initiated: {payment_id} for user {user_id}")
        
        return PaymentResponse(
            payment_id=payment_id,
            status='pending',
            checkout_request_id=result.get('Check
