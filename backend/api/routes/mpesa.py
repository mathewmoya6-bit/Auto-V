"""
M-Pesa Routes - FastAPI Version
Fully aligned with AUTO-V Platform
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from app.services.mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    query_payment_status,
    auto_confirm_payment,
    is_mpesa_configured,
    get_mpesa_token
)

logger = logging.getLogger(__name__)

# ─── Router ──────────────────────────────────────────────────
router = APIRouter(prefix="/api/mpesa", tags=["M-Pesa"])


# ─── Pydantic Models ──────────────────────────────────────

class MpesaInitiateRequest(BaseModel):
    """M-Pesa initiation request model"""
    phone: str = Field(..., description="Phone number (e.g., 0712345678)")
    amount: float = Field(..., description="Amount to pay", gt=0)
    payment_id: Optional[str] = Field(None, description="Optional payment ID")
    reference: Optional[str] = Field(None, description="Optional reference")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        cleaned = ''.join(c for c in v if c.isdigit())
        if len(cleaned) < 9 or len(cleaned) > 13:
            raise ValueError('Phone number must be between 9 and 13 digits')
        return v


class MpesaInitiateResponse(BaseModel):
    """M-Pesa initiation response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    """Payment status response model"""
    success: bool
    payment_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    phone: Optional[str] = None
    mpesa_receipt: Optional[str] = None
    reference: Optional[str] = None
    checkout_request_id: Optional[str] = None
    merchant_request_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None


class MpesaCallbackResponse(BaseModel):
    """M-Pesa callback response model"""
    ResultCode: int = 0
    ResultDesc: str = "Success"


class AutoConfirmResponse(BaseModel):
    """Auto-confirm response model"""
    success: bool
    status: Optional[str] = None
    result_code: Optional[str] = None
    result_desc: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class UserPaymentsResponse(BaseModel):
    """User payments response model"""
    success: bool
    user_id: str
    payments: list
    total: int
    error: Optional[str] = None


class TestResponse(BaseModel):
    """Test response model"""
    success: bool
    message: Optional[str] = None
    env: Optional[str] = None
    shortcode: Optional[str] = None
    configured: Optional[bool] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ─── Response Helper ──────────────────────────────────────

def create_response(success: bool, data: Any = None, error: str = None, status_code: int = 200):
    """Standard API response wrapper."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": success,
            "data": data,
            "error": error
        }
    )


# ─── Routes ──────────────────────────────────────────────

@router.post("/initiate", response_model=MpesaInitiateResponse)
async def initiate_payment(request: MpesaInitiateRequest):
    """
    Initiate M-Pesa STK Push payment.
    
    **Request Body:**
    - `phone`: Phone number (e.g., 0712345678)
    - `amount`: Amount to pay (must be > 0)
    - `payment_id`: Optional payment ID (auto-generated if not provided)
    - `reference`: Optional reference (auto-generated if not provided)
    - `user_id`: Optional user ID for tracking
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Contains `payment_id`, `checkout_request_id`, `merchant_request_id`
    - `error`: Error message if unsuccessful
    """
    try:
        # Generate IDs if not provided
        payment_id = request.payment_id or f"PAY-{uuid.uuid4().hex[:8].upper()}"
        reference = request.reference or f"AUTO-{uuid.uuid4().hex[:8].upper()}"

        logger.info(f"📤 Payment init: {payment_id} | {request.phone} | {request.amount}")

        result = initiate_stk_push(
            phone=request.phone,
            amount=request.amount,
            payment_id=payment_id,
            reference=reference,
            user_id=request.user_id
        )

        return create_response(
            success=True,
            data={
                "payment_id": payment_id,
                "checkout_request_id": result.get("CheckoutRequestID"),
                "merchant_request_id": result.get("MerchantRequestID")
            }
        )

    except Exception as e:
        logger.error(f"initiate error: {e}", exc_info=True)
        return create_response(
            success=False,
            error=str(e),
            status_code=500
        )


@router.get("/status/{payment_id}", response_model=PaymentStatusResponse)
async def get_payment_status(payment_id: str):
    """
    Get payment status by ID from database.
    
    **Path Parameter:**
    - `payment_id`: The payment ID to check
    
    **Response:**
    - `success`: Boolean indicating success
    - `payment_id`: The payment ID
    - `status`: Current payment status (pending, completed, failed)
    - `amount`: Payment amount
    - `phone`: Phone number used
    - `mpesa_receipt`: M-Pesa receipt number (if completed)
    - `reference`: Payment reference
    - `checkout_request_id`: M-Pesa checkout request ID
    - `merchant_request_id`: M-Pesa merchant request ID
    - `created_at`: Creation timestamp
    - `updated_at`: Last update timestamp
    - `error`: Error message if unsuccessful
    """
    try:
        from app.services.supabase_client import get_payment_by_payment_id
        payment = get_payment_by_payment_id(payment_id)
        
        if payment:
            return PaymentStatusResponse(
                success=True,
                payment_id=payment.get("payment_id"),
                status=payment.get("status", "pending"),
                amount=payment.get("amount"),
                phone=payment.get("phone"),
                mpesa_receipt=payment.get("mpesa_receipt"),
                reference=payment.get("reference"),
                checkout_request_id=payment.get("checkout_request_id"),
                merchant_request_id=payment.get("merchant_request_id"),
                created_at=payment.get("created_at"),
                updated_at=payment.get("updated_at")
            )
        else:
            return PaymentStatusResponse(
                success=False,
                error="Payment not found"
            )
            
    except Exception as e:
        logger.error(f"status error: {e}", exc_info=True)
        return PaymentStatusResponse(
            success=False,
            error=str(e)
        )


@router.post("/callback", response_model=MpesaCallbackResponse)
async def mpesa_callback(request: Request):
    """
    Handle M-Pesa callback from Safaricom.
    
    **Request Body:** M-Pesa callback payload from Safaricom
    
    **Response:** Always returns success to Safaricom to prevent retries
    """
    try:
        # Get raw data first for logging
        raw_data = await request.body()
        raw_str = raw_data.decode('utf-8')
        
        print("=" * 60)
        print("M-PESA CALLBACK RECEIVED")
        print(f"Raw data: {raw_str}")
        print("=" * 60)
        
        # Parse JSON
        try:
            data = await request.json()
        except Exception as json_err:
            logger.warning(f"Failed to parse JSON: {json_err}")
            data = None
        
        if not data:
            logger.warning("No JSON data in callback")
            print("❌ No JSON data received")
            return MpesaCallbackResponse(ResultCode=1, ResultDesc="No data")

        # Log the full callback data beautifully
        logger.info(f"📩 Callback received")
        print("📩 Parsed callback data:")
        print(json.dumps(data, indent=2))

        # Extract key information for quick debugging
        try:
            stk_callback = data.get("Body", {}).get("stkCallback", {})
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")
            checkout_id = stk_callback.get("CheckoutRequestID")
            merchant_id = stk_callback.get("MerchantRequestID")
            
            print(f"🔑 ResultCode: {result_code}")
            print(f"📝 ResultDesc: {result_desc}")
            print(f"🆔 CheckoutRequestID: {checkout_id}")
            print(f"🆔 MerchantRequestID: {merchant_id}")
            
            # Extract metadata if available
            metadata = stk_callback.get("CallbackMetadata", {})
            if metadata:
                items = metadata.get("Item", [])
                for item in items:
                    print(f"📊 {item.get('Name')}: {item.get('Value')}")
        except Exception as e:
            print(f"⚠️ Error extracting callback details: {e}")

        # Process the callback
        print("🔄 Processing callback...")
        result = handle_mpesa_callback(data)
        
        # Log the result
        logger.info(f"Callback processing result: {result}")
        print(f"✅ CALLBACK RESULT: {result}")

        # Always return success to Safaricom
        return MpesaCallbackResponse()

    except Exception as e:
        logger.error(f"callback error: {e}", exc_info=True)
        print(f"❌ CALLBACK ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        # Still return success to Safaricom to prevent retries
        return MpesaCallbackResponse(ResultDesc="Received")


@router.post("/auto-confirm/{payment_id}", response_model=AutoConfirmResponse)
async def auto_confirm(payment_id: str):
    """
    Auto-confirm a pending payment.
    
    **Path Parameter:**
    - `payment_id`: The payment ID to confirm
    
    **Response:**
    - `success`: Boolean indicating success
    - `status`: Updated payment status
    - `result_code`: M-Pesa result code
    - `result_desc`: M-Pesa result description
    - `data`: Additional data
    - `error`: Error message if unsuccessful
    """
    try:
        result = auto_confirm_payment(payment_id)
        return AutoConfirmResponse(
            success=True,
            status=result.get("status"),
            result_code=result.get("result_code"),
            result_desc=result.get("result_desc"),
            data=result.get("data")
        )

    except Exception as e:
        logger.error(f"auto-confirm error: {e}", exc_info=True)
        return AutoConfirmResponse(
            success=False,
            error=str(e)
        )


@router.get("/user/{user_id}", response_model=UserPaymentsResponse)
async def user_payments(
    user_id: str,
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get all payments for a user.
    
    **Path Parameter:**
    - `user_id`: The user ID
    
    **Query Parameters:**
    - `limit`: Number of payments to return (default: 50, max: 100)
    
    **Response:**
    - `success`: Boolean indicating success
    - `user_id`: The user ID
    - `payments`: List of payments
    - `total`: Total number of payments
    - `error`: Error message if unsuccessful
    """
    try:
        from app.services.supabase_client import get_user_payments
        payments = get_user_payments(user_id, limit)
        
        return UserPaymentsResponse(
            success=True,
            user_id=user_id,
            payments=payments,
            total=len(payments)
        )
    except Exception as e:
        logger.error(f"user payments error: {e}", exc_info=True)
        return UserPaymentsResponse(
            success=False,
            user_id=user_id,
            payments=[],
            total=0,
            error=str(e)
        )


@router.get("/query/{checkout_request_id}")
async def query_status(checkout_request_id: str):
    """
    Query payment status from Safaricom.
    
    **Path Parameter:**
    - `checkout_request_id`: M-Pesa checkout request ID
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Contains status, result_code, result_desc, receipt
    - `error`: Error message if unsuccessful
    """
    try:
        result = query_payment_status(checkout_request_id)
        return create_response(
            success=True,
            data=result
        )
    except Exception as e:
        logger.error(f"query error: {e}", exc_info=True)
        return create_response(
            success=False,
            error=str(e),
            status_code=500
        )


@router.get("/test", response_model=TestResponse)
async def test():
    """
    Test endpoint to verify M-Pesa API is working.
    
    **Response:**
    - `success`: Boolean indicating success
    - `message`: Status message
    - `env`: Current environment
    - `shortcode`: M-Pesa shortcode
    - `configured`: Whether M-Pesa is configured
    """
    return TestResponse(
        success=True,
        message="M-Pesa API working",
        env=os.getenv("MPESA_ENV", "production"),
        shortcode=os.getenv("MPESA_SHORTCODE", "4095377"),
        configured=is_mpesa_configured()
    )


@router.get("/test-db", response_model=TestResponse)
async def test_db():
    """
    Test Supabase database connection.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Contains connection status and payments
    - `error`: Error message if unsuccessful
    """
    try:
        from app.services.supabase_client import get_supabase_client, get_all_payments
        client = get_supabase_client()
        
        # Try to get payments
        payments = get_all_payments(limit=5)
        
        return TestResponse(
            success=True,
            message="Supabase connected",
            data={
                "supabase_connected": True,
                "payments_count": len(payments),
                "payments": payments
            }
        )
    except Exception as e:
        logger.error(f"test-db error: {e}", exc_info=True)
        return TestResponse(
            success=False,
            error=str(e)
        )


@router.get("/versions")
async def versions():
    """
    Get version information for debugging.
    
    **Response:** Version information for Python, supabase, httpx
    """
    try:
        import supabase
        import httpx
        import sys
        
        return {
            "python": sys.version,
            "supabase": getattr(supabase, "__version__", "unknown"),
            "httpx": getattr(httpx, "__version__", "unknown")
        }
    except Exception as e:
        return {
            "error": str(e),
            "supabase": "failed to import",
            "httpx": "failed to import"
        }


@router.get("/health")
async def health():
    """
    Health check for M-Pesa service.
    
    **Response:** Service health status
    """
    return {
        "status": "ok",
        "service": "mpesa",
        "environment": os.getenv("MPESA_ENV", "production"),
        "shortcode": os.getenv("MPESA_SHORTCODE", "4095377"),
        "configured": is_mpesa_configured(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/routes")
async def list_routes():
    """
    Debug: List all registered M-Pesa routes.
    
    **Response:** List of all available routes
    """
    return {
        "routes": [
            {"path": "/api/mpesa/initiate", "method": "POST"},
            {"path": "/api/mpesa/status/{payment_id}", "method": "GET"},
            {"path": "/api/mpesa/callback", "method": "POST"},
            {"path": "/api/mpesa/auto-confirm/{payment_id}", "method": "POST"},
            {"path": "/api/mpesa/user/{user_id}", "method": "GET"},
            {"path": "/api/mpesa/query/{checkout_request_id}", "method": "GET"},
            {"path": "/api/mpesa/test", "method": "GET"},
            {"path": "/api/mpesa/test-db", "method": "GET"},
            {"path": "/api/mpesa/versions", "method": "GET"},
            {"path": "/api/mpesa/health", "method": "GET"},
            {"path": "/api/mpesa/routes", "method": "GET"}
        ],
        "total": 11,
        "base_url": "/api/mpesa"
    }
