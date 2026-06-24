# ============================================================
# api/routes/mpesa.py - FastAPI M-Pesa Routes
# ============================================================

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
import httpx
import base64

from services.supabase_client import get_supabase_client
from services.mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    query_payment_status,
    auto_confirm_payment,
    is_mpesa_configured,
    get_mpesa_token
)

logger = logging.getLogger(__name__)

# ─── Router ──────────────────────────────────────────────────
router = APIRouter(tags=["M-Pesa"])

# ─── Request Models ──────────────────────────────────────────
class STKPushRequest(BaseModel):
    phone: str = Field(..., pattern=r'^[0-9]{10,12}$', description="Phone number (0712345678 or 254712345678)")
    amount: float = Field(..., gt=0, description="Amount to charge")
    payment_id: Optional[str] = None
    reference: Optional[str] = None
    user_id: Optional[str] = None

class STKPushResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# ─── Response Helper ──────────────────────────────────────────
def response(success: bool, data=None, error=None, status=200):
    payload = {"success": success}
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    return payload, status

# ─── Routes ──────────────────────────────────────────────────

@router.post("/initiate", response_model=STKPushResponse)
async def initiate_payment(request: STKPushRequest):
    """Initiate M-Pesa STK Push payment."""
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
    """Get payment status by ID."""
    try:
        client = get_supabase_client()
        
        # Try different ID formats
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
    """Handle M-Pesa callback from Safaricom."""
    try:
        data = await request.json()
        logger.info(f"📩 Callback received: {data}")
        
        result = handle_mpesa_callback(data)
        return result

    except Exception as e:
        logger.error(f"callback error: {e}", exc_info=True)
        return {"ResultCode": 1, "ResultDesc": "System error"}

@router.post("/auto-confirm/{payment_id}")
async def auto_confirm(payment_id: str):
    """Auto-confirm a pending payment."""
    try:
        client = get_supabase_client()
        
        # Find payment
        for field in ["payment_id", "checkout_request_id", "mpesa_code"]:
            result = client.table("payments").select("*").eq(field, payment_id).execute()
            if result.data:
                payment = result.data[0]
                break
        else:
            return response(False, error="Payment not found", status=404)
        
        result = auto_confirm_payment(payment["id"])
        return response(True, result)

    except Exception as e:
        logger.error(f"auto-confirm error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)

@router.get("/user/{user_id}")
async def user_payments(user_id: str, limit: int = 50):
    """Get all payments for a user."""
    try:
        client = get_supabase_client()
        result = client.table("payments")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return response(True, {"payments": result.data})

    except Exception as e:
        logger.error(f"user payments error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)

@router.get("/query/{checkout_request_id}")
async def query_status(checkout_request_id: str):
    """Query payment status from Safaricom."""
    try:
        result = query_payment_status(checkout_request_id)
        return response(True, result)

    except Exception as e:
        logger.error(f"query error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)

@router.get("/health")
async def health():
    """Health check for M-Pesa service."""
    return {
        "status": "ok",
        "service": "mpesa",
        "environment": os.getenv("MPESA_ENV", "production"),
        "shortcode": os.getenv("MPESA_SHORTCODE", "4095377"),
        "configured": is_mpesa_configured(),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/test")
async def test():
    """Test endpoint to verify M-Pesa API is working."""
    return {
        "success": True,
        "message": "M-Pesa API working",
        "env": os.getenv("MPESA_ENV", "production"),
        "shortcode": os.getenv("MPESA_SHORTCODE", "4095377"),
        "configured": is_mpesa_configured()
    }

@router.get("/routes")
async def list_routes():
    """Debug: List all registered M-Pesa routes."""
    return {
        "routes": [
            {"path": "/api/mpesa/initiate", "method": "POST"},
            {"path": "/api/mpesa/status/{payment_id}", "method": "GET"},
            {"path": "/api/mpesa/callback", "method": "POST"},
            {"path": "/api/mpesa/auto-confirm/{payment_id}", "method": "POST"},
            {"path": "/api/mpesa/user/{user_id}", "method": "GET"},
            {"path": "/api/mpesa/query/{checkout_request_id}", "method": "GET"},
            {"path": "/api/mpesa/health", "method": "GET"},
            {"path": "/api/mpesa/test", "method": "GET"}
        ],
        "total": 8,
        "base_url": "/api/mpesa"
    }
