# ============================================================
# services/mpesa.py - M-Pesa Service Logic
# ============================================================

import os
import base64
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

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


def get_mpesa_token() -> Optional[str]:
    """Get M-Pesa OAuth token."""
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
            "CallBackURL": os.getenv("MPESA_CALLBACK_URL", "https://auto-v.meipressgroup.com/api/mpesa/callback"),
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
            logger.info(f"STK Push initiated: {result.get('CheckoutRequestID')}")
            return result
        else:
            logger.error(f"STK Push failed: {response.status_code}")
            raise ValueError(f"STK Push failed: {response.text}")

    except Exception as e:
        logger.error(f"STK Push error: {e}")
        raise


def handle_mpesa_callback(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle M-Pesa callback from Safaricom."""
    try:
        body = data.get("Body", {})
        stk_callback = body.get("stkCallback", {})

        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        merchant_request_id = stk_callback.get("MerchantRequestID")

        # Extract metadata
        metadata = stk_callback.get("CallbackMetadata", {})
        items = metadata.get("Item", [])

        meta_dict = {}
        for item in items:
            name = item.get("Name")
            value = item.get("Value")
            if name:
                meta_dict[name] = value

        status = "completed" if result_code == 0 else "failed"

        logger.info(
            f"Callback: {checkout_request_id} -> {status}",
            extra={
                "result_code": result_code,
                "result_desc": result_desc,
                "mpesa_code": meta_dict.get("MpesaReceiptNumber"),
                "amount": meta_dict.get("Amount")
            }
        )

        return {
            "ResultCode": 0,
            "ResultDesc": "Success",
            "data": {
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
                "status": status,
                "result_code": result_code,
                "result_desc": result_desc,
                "mpesa_code": meta_dict.get("MpesaReceiptNumber"),
                "amount": meta_dict.get("Amount"),
                "transaction_date": meta_dict.get("TransactionDate")
            }
        }

    except Exception as e:
        logger.error(f"Callback handling error: {e}")
        return {"ResultCode": 1, "ResultDesc": f"Error: {str(e)}"}


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


def auto_confirm_payment(payment_id: str) -> Dict[str, Any]:
    """Auto-confirm a pending payment (admin override)."""
    try:
        # This would typically update a database record
        # For now, return success
        return {
            "success": True,
            "message": "Payment auto-confirmed",
            "payment_id": payment_id
        }

    except Exception as e:
        logger.error(f"Auto-confirm error: {e}")
        raise


def is_mpesa_configured() -> bool:
    """Check if M-Pesa is properly configured."""
    return bool(
        MPESA_CONSUMER_KEY and
        MPESA_CONSUMER_SECRET and
        MPESA_PASSKEY
    )


def get_mpesa_token_public() -> Optional[Dict[str, Any]]:
    """Public wrapper for get_mpesa_token."""
    token = get_mpesa_token()
    if token:
        return {"token": token, "expires_in": 3600}
    return None


# ─── Alias for backward compatibility ──────────────────────
mpesa_service = handle_mpesa_callback


__all__ = [
    "get_mpesa_token",
    "initiate_stk_push",
    "handle_mpesa_callback",
    "query_payment_status",
    "auto_confirm_payment",
    "is_mpesa_configured",
    "get_mpesa_token_public",
    "mpesa_service"
]
