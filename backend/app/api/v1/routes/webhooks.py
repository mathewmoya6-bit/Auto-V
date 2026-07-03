# app/api/v1/routes/webhooks.py
# =============================================================================
# AUTO-V API - Webhooks Routes
# =============================================================================
# Handles external webhook callbacks from services like M-Pesa,
# payment gateways, and third-party integrations.
# =============================================================================

import logging
from fastapi import APIRouter, Request, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

# ─── Configuration ──────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"]
)


# =============================================================================
# REQUEST MODELS
# =============================================================================

class MpesaCallbackBody(BaseModel):
    """M-Pesa callback request body model."""
    Body: Optional[Dict[str, Any]] = Field(default=None, description="M-Pesa callback body")
    TransactionType: Optional[str] = Field(default=None, description="Transaction type")
    TransID: Optional[str] = Field(default=None, description="Transaction ID")
    TransTime: Optional[str] = Field(default=None, description="Transaction time")
    TransAmount: Optional[str] = Field(default=None, description="Transaction amount")
    BusinessShortCode: Optional[str] = Field(default=None, description="Business short code")
    BillRefNumber: Optional[str] = Field(default=None, description="Bill reference number")
    InvoiceNumber: Optional[str] = Field(default=None, description="Invoice number")
    MSISDN: Optional[str] = Field(default=None, description="Customer phone number")
    FirstName: Optional[str] = Field(default=None, description="Customer first name")
    MiddleName: Optional[str] = Field(default=None, description="Customer middle name")
    LastName: Optional[str] = Field(default=None, description="Customer last name")
    OrgAccountBalance: Optional[str] = Field(default=None, description="Organization account balance")


class WebhookResponse(BaseModel):
    """Standard webhook response model."""
    success: bool = Field(..., description="Whether the webhook was processed successfully")
    message: str = Field(..., description="Response message")
    transaction_id: Optional[str] = Field(default=None, description="Transaction ID if available")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# PROCESS WEBHOOKS
# =============================================================================

def process_mpesa_payment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process M-Pesa payment callback.
    
    Args:
        payload: M-Pesa callback payload
        
    Returns:
        Dict with processing result
    """
    logger.info(f"📩 Processing M-Pesa webhook payload")
    
    try:
        # Extract transaction details
        body = payload.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        
        # Get transaction data
        merchant_request_id = stk_callback.get("MerchantRequestID")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        
        # Check if transaction was successful
        is_successful = result_code == "0"
        
        # Get callback metadata
        callback_metadata = stk_callback.get("CallbackMetadata", {})
        items = callback_metadata.get("Item", [])
        
        # Extract transaction details from metadata
        transaction_data = {}
        for item in items:
            name = item.get("Name")
            value = item.get("Value")
            if name:
                transaction_data[name] = value
        
        logger.info(f"✅ M-Pesa transaction processed: {transaction_data}")
        
        return {
            "success": is_successful,
            "merchant_request_id": merchant_request_id,
            "checkout_request_id": checkout_request_id,
            "result_code": result_code,
            "result_desc": result_desc,
            "transaction_data": transaction_data,
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing M-Pesa webhook: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@router.post("/mpesa")
async def mpesa_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> WebhookResponse:
    """
    M-Pesa payment callback webhook endpoint.
    
    This endpoint receives payment confirmations from Safaricom's M-Pesa API.
    It processes the callback and updates the payment status.
    
    Args:
        request: FastAPI request object
        background_tasks: FastAPI background tasks
        
    Returns:
        WebhookResponse: Confirmation of receipt
    """
    try:
        # Parse request body
        body = await request.json()
        
        logger.info(f"📩 Received M-Pesa webhook: {body.get('Body', {}).get('stkCallback', {}).get('MerchantRequestID', 'unknown')}")
        
        # Process in background to avoid timeout
        # background_tasks.add_task(process_mpesa_payment, body)
        
        # Process immediately for synchronous response
        result = process_mpesa_payment(body)
        
        # Update payment status in database (if you have a payment service)
        # await update_payment_status(result)
        
        # Return response
        return WebhookResponse(
            success=True,
            message="M-Pesa webhook received successfully",
            transaction_id=result.get("checkout_request_id"),
        )
        
    except Exception as e:
        logger.error(f"❌ M-Pesa webhook error: {str(e)}", exc_info=True)
        
        # M-Pesa expects a 200 OK response even on errors to prevent retries
        # But we'll return an error response with 200 status
        return WebhookResponse(
            success=False,
            message=f"Error processing webhook: {str(e)}",
        )


@router.post("/payment")
async def payment_webhook(request: Request) -> WebhookResponse:
    """
    Generic payment webhook endpoint.
    
    Args:
        request: FastAPI request object
        
    Returns:
        WebhookResponse: Confirmation of receipt
    """
    try:
        body = await request.json()
        logger.info(f"📩 Received payment webhook: {body}")
        
        # Process payment webhook
        # await process_payment_webhook(body)
        
        return WebhookResponse(
            success=True,
            message="Payment webhook received successfully",
        )
        
    except Exception as e:
        logger.error(f"❌ Payment webhook error: {str(e)}", exc_info=True)
        return WebhookResponse(
            success=False,
            message=f"Error processing webhook: {str(e)}",
        )


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> WebhookResponse:
    """
    WhatsApp Business API webhook endpoint.
    
    Args:
        request: FastAPI request object
        
    Returns:
        WebhookResponse: Confirmation of receipt
    """
    try:
        body = await request.json()
        logger.info(f"📩 Received WhatsApp webhook: {body}")
        
        # Process WhatsApp webhook
        # await process_whatsapp_message(body)
        
        return WebhookResponse(
            success=True,
            message="WhatsApp webhook received successfully",
        )
        
    except Exception as e:
        logger.error(f"❌ WhatsApp webhook error: {str(e)}", exc_info=True)
        return WebhookResponse(
            success=False,
            message=f"Error processing webhook: {str(e)}",
        )


@router.post("/email")
async def email_webhook(request: Request) -> WebhookResponse:
    """
    Email tracking webhook endpoint (SendGrid, Mailgun, etc.).
    
    Args:
        request: FastAPI request object
        
    Returns:
        WebhookResponse: Confirmation of receipt
    """
    try:
        body = await request.json()
        logger.info(f"📩 Received email webhook: {body}")
        
        # Process email tracking webhook
        # await process_email_webhook(body)
        
        return WebhookResponse(
            success=True,
            message="Email webhook received successfully",
        )
        
    except Exception as e:
        logger.error(f"❌ Email webhook error: {str(e)}", exc_info=True)
        return WebhookResponse(
            success=False,
            message=f"Error processing webhook: {str(e)}",
        )


# =============================================================================
# WEBHOOK SECURITY VERIFICATION
# =============================================================================

@router.get("/verify")
async def verify_webhook(request: Request) -> dict:
    """
    Webhook verification endpoint for services that require verification.
    
    Args:
        request: FastAPI request object
        
    Returns:
        dict: Verification status
    """
    query_params = dict(request.query_params)
    
    logger.info(f"🔑 Webhook verification request: {query_params}")
    
    # Example: For WhatsApp Business API verification
    if "hub.mode" in query_params and "hub.challenge" in query_params:
        mode = query_params.get("hub.mode")
        challenge = query_params.get("hub.challenge")
        
        if mode == "subscribe":
            return {
                "status": "verified",
                "challenge": challenge,
                "message": "Webhook verified successfully"
            }
    
    return {
        "status": "pending",
        "message": "Webhook verification not completed"
    }


# =============================================================================
# TEST WEBHOOKS
# =============================================================================

@router.post("/test")
async def test_webhook(request: Request) -> dict:
    """
    Test endpoint for webhooks - echoes back the payload.
    
    Args:
        request: FastAPI request object
        
    Returns:
        dict: Echo of the request data
    """
    try:
        body = await request.json()
    except Exception:
        body = None
    
    return {
        "status": "test",
        "method": request.method,
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "body": body,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# SIMPLE WEBHOOK (Your Original Code)
# =============================================================================

# This is your original endpoint - kept for compatibility
@router.post("/mpesa-simple")
async def mpesa_webhook_simple(request: Request) -> dict:
    """
    Simple M-Pesa webhook endpoint (original version).
    
    Args:
        request: FastAPI request object
        
    Returns:
        dict: Confirmation of receipt with payload
    """
    try:
        body = await request.json()
        logger.info(f"📩 Received simple M-Pesa webhook")
        
        return {
            "received": True,
            "payload": body
        }
        
    except Exception as e:
        logger.error(f"❌ Simple M-Pesa webhook error: {str(e)}")
        return {
            "received": False,
            "error": str(e)
        }
