# ============================================================
# services/mpesa.py - No WebSocket Dependency
# ============================================================

import os
import json
import logging
import base64
import requests
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ─── M-Pesa Configuration ──────────────────────────────────
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "4095377")
MPESA_ENV = os.getenv("MPESA_ENV", "production").lower().strip()

# ─── Base URLs ─────────────────────────────────────────────
BASE_URLS = {
    "production": "https://api.safaricom.co.ke",
    "sandbox": "https://sandbox.safaricom.co.ke"
}
BASE_URL = BASE_URLS.get(MPESA_ENV, BASE_URLS["production"])


# ─── Get M-Pesa Token ──────────────────────────────────────
def get_mpesa_token() -> Optional[str]:
    """Get M-Pesa OAuth token with retry."""
    try:
        if not MPESA_CONSUMER_KEY or not MPESA_CONSUMER_SECRET:
            logger.error("M-Pesa credentials not configured")
            return None

        auth = base64.b64encode(
            f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()
        ).decode()

        response = requests.get(
            f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth}"},
            timeout=30
        )

        if response.status_code == 200:
            token = response.json().get("access_token")
            logger.info("M-Pesa token obtained successfully")
            return token
        else:
            logger.error(f"Failed to get M-Pesa token: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"M-Pesa token error: {e}")
        return None


# ─── Initiate STK Push ─────────────────────────────────────
def initiate_stk_push(
    phone: str,
    amount: float,
    payment_id: str,
    reference: str = None,
    user_id: str = None
) -> Dict[str, Any]:
    """Initiate M-Pesa STK Push payment."""
    try:
        token = get_mpesa_token()
        if not token:
            raise ValueError("Failed to get M-Pesa token")

        # Format phone number
        if phone.startswith("0"):
            phone = "254" + phone[1:]
        elif not phone.startswith("254"):
            phone = "254" + phone

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()

        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(round(amount)),
            "PartyA": phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": os.getenv("MPESA_CALLBACK_URL", "https://your-domain.com/api/mpesa/callback"),
            "AccountReference": reference or f"AUTO-{payment_id[-8:]}",
            "TransactionDesc": f"Payment {payment_id}"
        }

        if user_id:
            payload["TransactionDesc"] = f"{payload['TransactionDesc']} - User {user_id}"

        response = requests.post(
            f"{BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            
            # Save to Supabase
            try:
                from services.supabase_client import get_supabase_client
                client = get_supabase_client()
                client.table("payments").insert({
                    "payment_id": payment_id,
                    "user_id": user_id,
                    "phone": phone,
                    "amount": amount,
                    "status": "pending",
                    "checkout_request_id": result.get("CheckoutRequestID"),
                    "merchant_request_id": result.get("MerchantRequestID"),
                    "reference": reference,
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
                logger.info(f"Payment {payment_id} saved to database")
            except Exception as e:
                logger.warning(f"Failed to save payment to database: {e}")

            return result
        else:
            logger.error(f"STK Push failed: {response.status_code} - {response.text}")
            raise ValueError(f"STK Push failed: {response.text}")

    except Exception as e:
        logger.error(f"STK Push error: {e}")
        raise


# ─── Handle M-Pesa Callback ───────────────────────────────
def handle_mpesa_callback(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle M-Pesa callback from Safaricom."""
    try:
        body = data.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        merchant_request_id = stk_callback.get("MerchantRequestID")
        
        metadata = stk_callback.get("CallbackMetadata", {})
        items = metadata.get("Item", [])
        
        meta_dict = {}
        for item in items:
            name = item.get("Name")
            value = item.get("Value")
            if name:
                meta_dict[name] = value
        
        status = "completed" if result_code == 0 else "failed"
        
        # Update payment in Supabase
        try:
            from services.supabase_client import get_supabase_client, update_payment_by_checkout_id
            client = get_supabase_client()
            
            update_data = {
                "status": status,
                "result_code": result_code,
                "result_desc": result_desc,
                "mpesa_code": meta_dict.get("MpesaReceiptNumber"),
                "transaction_date": meta_dict.get("TransactionDate"),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = client.table("payments")\
                .update(update_data)\
                .eq("checkout_request_id", checkout_request_id)\
                .execute()
            
            if result.data:
                logger.info(f"Payment {checkout_request_id} updated: {status}")
            else:
                logger.warning(f"Payment {checkout_request_id} not found")
                
        except Exception as e:
            logger.error(f"Failed to update payment: {e}")

        return {
            "ResultCode": 0,
            "ResultDesc": "Success"
        }

    except Exception as e:
        logger.error(f"Callback handling error: {e}")
        return {
            "ResultCode": 1,
            "ResultDesc": f"Error: {str(e)}"
        }


# ─── Query Payment Status ──────────────────────────────────
def query_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    """Query payment status from Safaricom."""
    try:
        token = get_mpesa_token()
        if not token:
            raise ValueError("Failed to get M-Pesa token")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()

        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }

        response = requests.post(
            f"{BASE_URL}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Query failed: {response.status_code}")
            raise ValueError(f"Query failed: {response.text}")

    except Exception as e:
        logger.error(f"Query error: {e}")
        raise


# ─── Auto-Confirm Payment ──────────────────────────────────
def auto_confirm_payment(payment_id: str) -> Dict[str, Any]:
    """Auto-confirm a pending payment (admin override)."""
    try:
        from services.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        result = client.table("payments")\
            .update({
                "status": "completed",
                "auto_confirmed": True,
                "auto_confirmed_at": datetime.utcnow().isoformat()
            })\
            .eq("id", payment_id)\
            .execute()
        
        if result.data:
            return {
                "success": True,
                "message": "Payment auto-confirmed",
                "payment": result.data[0]
            }
        else:
            return {
                "success": False,
                "message": "Payment not found"
            }

    except Exception as e:
        logger.error(f"Auto-confirm error: {e}")
        raise


# ─── Check if M-Pesa is Configured ─────────────────────────
def is_mpesa_configured() -> bool:
    """Check if M-Pesa is properly configured."""
    return bool(
        MPESA_CONSUMER_KEY and 
        MPESA_CONSUMER_SECRET and 
        MPESA_PASSKEY
    )


# ─── Get M-Pesa Token (Public) ────────────────────────────
def get_mpesa_token_public() -> Optional[Dict[str, Any]]:
    """Public wrapper for get_mpesa_token."""
    token = get_mpesa_token()
    if token:
        return {"token": token, "expires_in": 3600}
    return None
