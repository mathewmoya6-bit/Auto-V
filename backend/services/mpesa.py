"""
M-Pesa Service Layer - FastAPI Version
Handles M-Pesa API interactions and business logic
"""

import os
import uuid
import json
import logging
import base64
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from supabase import create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Supabase Client ──────────────────────────────────────

def get_supabase_client():
    """Get Supabase client instance"""
    try:
        client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        return client
    except Exception as e:
        logger.error(f"Supabase connection error: {e}")
        return None


# ─── Configuration ──────────────────────────────────────

MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "4095377")
MPESA_ENV = os.getenv("MPESA_ENV", "production")
MPESA_API_BASE = (
    "https://api.safaricom.co.ke" if MPESA_ENV == "production"
    else "https://sandbox.safaricom.co.ke"
)


def is_mpesa_configured() -> bool:
    """Check if M-Pesa credentials are configured"""
    return all([
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_PASSKEY,
        MPESA_SHORTCODE
    ])


# ─── M-Pesa API Functions ──────────────────────────────

def get_mpesa_token() -> Optional[str]:
    """Get M-Pesa OAuth token"""
    if not is_mpesa_configured():
        logger.error("M-Pesa not configured")
        return None
    
    auth_str = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
    auth_bytes = auth_str.encode()
    auth_b64 = base64.b64encode(auth_bytes).decode()
    
    response = requests.get(
        f"{MPESA_API_BASE}/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {auth_b64}"},
        timeout=30
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to get M-Pesa token: {response.text}")
        return None
    
    return response.json()["access_token"]


def format_phone(phone: str) -> str:
    """Format phone number for M-Pesa"""
    cleaned = ''.join(c for c in phone if c.isdigit())
    if cleaned.startswith('0'):
        cleaned = '254' + cleaned[1:]
    elif cleaned.startswith('7') and len(cleaned) == 9:
        cleaned = '254' + cleaned
    elif len(cleaned) == 10 and cleaned.startswith('07'):
        cleaned = '254' + cleaned[1:]
    return cleaned


def initiate_stk_push(
    phone: str,
    amount: float,
    payment_id: str,
    reference: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Initiate STK Push payment"""
    try:
        formatted_phone = format_phone(phone)
        
        # Generate timestamp and password
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        data = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(data.encode()).decode()
        
        # Get access token
        access_token = get_mpesa_token()
        if not access_token:
            return {"error": "Failed to get M-Pesa token"}
        
        # Prepare payload
        callback_url = f"{settings.BASE_URL}/api/mpesa/callback"
        
        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": formatted_phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": formatted_phone,
            "CallBackURL": callback_url,
            "AccountReference": reference,
            "TransactionDesc": f"AUTO-V Payment {payment_id}"
        }
        
        logger.info(f"📤 STK Push payload: {payload}")
        
        response = requests.post(
            f"{MPESA_API_BASE}/mpesa/stkpush/v1/processrequest",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"STK Push error: {response.text}")
            return {"error": f"STK Push failed: {response.text}"}
        
        result = response.json()
        logger.info(f"📥 STK Push response: {result}")
        
        # Store in database
        client = get_supabase_client()
        if client:
            client.table("mpesa_transactions").insert({
                "payment_id": payment_id,
                "checkout_request_id": result.get("CheckoutRequestID"),
                "merchant_request_id": result.get("MerchantRequestID"),
                "phone": formatted_phone,
                "amount": int(amount),
                "reference": reference,
                "user_id": user_id,
                "status": "pending",
                "mpesa_response": result,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        
        return result
        
    except Exception as e:
        logger.error(f"initiate_stk_push error: {e}", exc_info=True)
        return {"error": str(e)}


def handle_mpesa_callback(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process M-Pesa callback"""
    try:
        stk_callback = data.get("Body", {}).get("stkCallback", {})
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        
        if not checkout_request_id:
            logger.warning("No checkout_request_id in callback")
            return {"error": "No checkout_request_id"}
        
        # Get metadata
        metadata_items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        amount = None
        mpesa_receipt = None
        phone = None
        
        for item in metadata_items:
            if item.get("Name") == "Amount":
                amount = item.get("Value")
            elif item.get("Name") == "MpesaReceiptNumber":
                mpesa_receipt = item.get("Value")
            elif item.get("Name") == "PhoneNumber":
                phone = item.get("Value")
        
        # Determine status
        status = "pending"
        if result_code == "0" or result_code == "000":
            status = "completed"
        elif str(result_code) in ["1", "1037", "1032", "2001", "2002"]:
            status = "failed"
        
        # Update database
        client = get_supabase_client()
        if client:
            client.table("mpesa_transactions").update({
                "status": status,
                "mpesa_result_code": str(result_code),
                "mpesa_result_desc": result_desc,
                "mpesa_receipt": mpesa_receipt,
                "mpesa_phone": phone,
                "mpesa_amount": amount,
                "callback_data": stk_callback,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("checkout_request_id", checkout_request_id).execute()
        
        return {
            "success": True,
            "status": status,
            "checkout_request_id": checkout_request_id,
            "result_code": result_code,
            "result_desc": result_desc,
            "receipt": mpesa_receipt,
            "amount": amount,
            "phone": phone
        }
        
    except Exception as e:
        logger.error(f"handle_mpesa_callback error: {e}", exc_info=True)
        return {"error": str(e)}


def query_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    """Query payment status from M-Pesa"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        data = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(data.encode()).decode()
        
        access_token = get_mpesa_token()
        if not access_token:
            return {"error": "Failed to get M-Pesa token"}
        
        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        response = requests.post(
            f"{MPESA_API_BASE}/mpesa/stkpushquery/v1/query",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Query error: {response.text}")
            return {"error": f"Query failed: {response.text}"}
        
        result = response.json()
        result_code = result.get("ResultCode") or result.get("ResponseCode")
        result_desc = result.get("ResultDesc") or result.get("ResponseDescription")
        
        status = "pending"
        if result_code == "0" or result_code == "000":
            status = "completed"
        elif str(result_code) in ["1", "1037", "1032", "2001", "2002"]:
            status = "failed"
        
        # Update database
        client = get_supabase_client()
        if client:
            client.table("mpesa_transactions").update({
                "status": status,
                "mpesa_result_code": str(result_code),
                "mpesa_result_desc": result_desc,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("checkout_request_id", checkout_request_id).execute()
        
        return {
            "success": True,
            "status": status,
            "result_code": result_code,
            "result_desc": result_desc,
            "receipt": result.get("MpesaReceiptNumber")
        }
        
    except Exception as e:
        logger.error(f"query_payment_status error: {e}", exc_info=True)
        return {"error": str(e)}


def auto_confirm_payment(payment_id: str) -> Dict[str, Any]:
    """Auto-confirm a pending payment"""
    try:
        # Get payment from database
        client = get_supabase_client()
        if not client:
            return {"error": "Supabase client not available"}
        
        result = client.table("mpesa_transactions").select("*").eq("payment_id", payment_id).execute()
        payments = result.data if hasattr(result, 'data') else result
        
        if not payments:
            return {"error": "Payment not found"}
        
        payment = payments[0]
        checkout_request_id = payment.get("checkout_request_id")
        
        if not checkout_request_id:
            return {"error": "No checkout_request_id"}
        
        if payment.get("status") == "completed":
            return {
                "status": "completed",
                "result_code": "0",
                "data": {"already_completed": True}
            }
        
        # Query M-Pesa
        query_result = query_payment_status(checkout_request_id)
        
        return query_result
        
    except Exception as e:
        logger.error(f"auto_confirm_payment error: {e}", exc_info=True)
        return {"error": str(e)}
