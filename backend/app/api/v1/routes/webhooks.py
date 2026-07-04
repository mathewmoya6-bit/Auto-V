# app/api/v1/routes/webhooks.py
# =============================================================================
# AUTO-V API - Webhooks Routes
# =============================================================================

import logging
from fastapi import APIRouter, Request, HTTPException, status
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/mpesa")
async def mpesa_webhook(request: Request):
    """M-Pesa payment callback webhook."""
    try:
        body = await request.json()
        logger.info(f"📩 Received M-Pesa webhook: {body}")
        return {"received": True, "payload": body}
    except Exception as e:
        logger.error(f"❌ M-Pesa webhook error: {str(e)}")
        return {"received": False, "error": str(e)}


@router.post("/payment")
async def payment_webhook(request: Request):
    """Generic payment webhook."""
    try:
        body = await request.json()
        logger.info(f"📩 Received payment webhook: {body}")
        return {"received": True, "payload": body}
    except Exception as e:
        logger.error(f"❌ Payment webhook error: {str(e)}")
        return {"received": False, "error": str(e)}
