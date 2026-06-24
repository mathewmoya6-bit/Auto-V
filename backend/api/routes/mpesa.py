# ============================================================
# api/routes/mpesa.py - FastAPI M-Pesa Routes
# ============================================================

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from services.supabase_client import get_supabase_client
from services.mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    query_payment_status,
    auto_confirm_payment,
    is_mpesa_configured
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["M-Pesa"])

# ─── Models ──────────────────────────────────────────────────
class STKPushRequest(BaseModel):
    phone: str = Field(..., pattern=r'^[0-9]{10,12}$')
    amount: float = Field(..., gt=0)
    payment_id: Optional[str] = None
    reference: Optional[str] = None
    user_id: Optional[str] = None

def response(success: bool, data=None, error=None, status=200):
    payload = {"success": success}
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    return payload, status

# ─── Routes ──────────────────────────────────────────────────

@router.post("/initiate")
async def initiate_payment(request: STKPushRequest):
    try:
        logger.info(f"📤 Payment init: {request.phone} | {request.amount}")
        
        payment_id = request.payment_id or f"PAY-{uuid.uuid4().hex[:8].upper()}"
        reference = request.reference or f"AUTO-{uuid.uuid4().hex[:8].upper()}"
        
        result = initiate_stk_push(
            phone=request.phone,
            amount=request.amount,
            payment_id=payment_id,
            reference=reference,
            user_id=request.user_id
        )
        
        return response(True, {
            "payment_id": payment_id,
            "checkout_request_id": result.get("CheckoutRequestID"),
            "merchant_request_id": result.get("MerchantRequestID")
        })
    except Exception as e:
        logger.error(f"initiate error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)

@router.get("/status/{payment_id}")
async def get_payment_status(payment_id: str):
    try:
        client = get_supabase_client()
        for field in ["payment_id", "checkout_request_id", "mpesa_code"]:
            result = client.table("payments").select("*").eq(field, payment_id).execute()
            if result.data:
                return response(True, result.data[0])
        return response(True, {"status": "not_found"})
    except Exception as e:
        logger.error(f"status error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)

@router.post("/callback")
async def mpesa_callback(request: Request):
    try:
        data = await request.json()
        logger.info(f"📩 Callback received")
        result = handle_mpesa_callback(data)
        return result
    except Exception as e:
        logger.error(f"callback error: {e}", exc_info=True)
        return {"ResultCode": 1, "ResultDesc": "System error"}

@router.get("/test")
async def test():
    return {
        "success": True,
        "message": "M-Pesa API working",
        "env": os.getenv("MPESA_ENV", "production"),
        "shortcode": os.getenv("MPESA_SHORTCODE", "4095377"),
        "configured": is_mpesa_configured()
    }

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "mpesa",
        "environment": os.getenv("MPESA_ENV", "production"),
        "shortcode": os.getenv("MPESA_SHORTCODE", "4095377"),
        "configured": is_mpesa_configured(),
        "timestamp": datetime.utcnow().isoformat()
    }
