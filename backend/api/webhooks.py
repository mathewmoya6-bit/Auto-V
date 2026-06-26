"""
Webhook Routes - FastAPI Version
Handles incoming webhooks from M-Pesa and other third-party services
"""

import logging
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.mpesa import handle_mpesa_callback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


# ─── Pydantic Models ──────────────────────────────────────────

class WebhookResponse(BaseModel):
    """Standard webhook response"""
    status: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class MpesaWebhookData(BaseModel):
    """M-Pesa webhook data model"""
    Body: Optional[Dict[str, Any]] = None


# ─── Routes ──────────────────────────────────────────────────

@router.post("/mpesa", response_model=WebhookResponse)
async def mpesa_webhook(request: Request):
    """
    Handle M-Pesa webhook callbacks from Safaricom.
    
    **Request Body:** M-Pesa callback payload from Safaricom
    
    **Response:**
    - `status`: Status of the webhook processing
    - `message`: Processing message
    - `data`: Additional data if any
    """
    try:
        # Get raw request data
        body = await request.body()
        raw_data = body.decode('utf-8')
        
        # Parse JSON
        try:
            data = await request.json()
        except Exception as json_err:
            logger.warning(f"Failed to parse JSON: {json_err}")
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Invalid JSON payload"
                }
            )
        
        if not data:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "No data received"
                }
            )
        
        logger.info(f"📩 Webhook received from M-Pesa")
        logger.info(f"📦 Webhook data: {data}")
        
        # Process the webhook
        result = handle_mpesa_callback(data)
        
        if result.get("error"):
            logger.error(f"Webhook processing error: {result['error']}")
            return JSONResponse(
                status_code=200,  # Always return 200 to M-Pesa
                content={
                    "status": "processed",
                    "message": result.get("error", "Processing completed with errors"),
                    "data": result
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Webhook processed successfully",
                "data": result
            }
        )
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        # Always return 200 to prevent M-Pesa from retrying
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": f"Processing error: {str(e)}"
            }
        )


@router.get("/health", response_model=WebhookResponse)
async def webhook_health():
    """
    Health check for webhook service.
    
    **Response:**
    - `status`: Service status
    - `service`: Service name
    """
    return WebhookResponse(
        status="ok",
        message="Webhook service is healthy",
        data={"service": "webhooks", "timestamp": "2024-01-01T00:00:00Z"}
    )


@router.get("/mpesa/verify", response_model=WebhookResponse)
async def verify_mpesa_webhook():
    """
    Verify M-Pesa webhook configuration.
    This endpoint is used to test if the webhook URL is reachable.
    
    **Response:**
    - `status`: Verification status
    - `message`: Verification message
    """
    return WebhookResponse(
        status="ok",
        message="M-Pesa webhook endpoint is reachable",
        data={
            "endpoint": "/api/webhooks/mpesa",
            "method": "POST",
            "requires": "JSON payload"
        }
    )


@router.post("/test", response_model=WebhookResponse)
async def test_webhook(request: Request):
    """
    Test endpoint for webhook simulation.
    Used for development and testing purposes.
    
    **Request Body:** Any JSON payload
    
    **Response:**
    - `status`: Test status
    - `message`: Test message
    - `data`: Echo of the received data
    """
    try:
        data = await request.json()
        logger.info(f"🧪 Test webhook received: {data}")
        
        return WebhookResponse(
            status="success",
            message="Test webhook received successfully",
            data={
                "received": data,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )
        
    except Exception as e:
        return WebhookResponse(
            status="error",
            message=f"Test webhook error: {str(e)}"
        )
