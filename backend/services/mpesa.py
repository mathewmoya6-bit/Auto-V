# services/mpesa.py - Production Ready v5 (Aligned)

import os
import base64
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from services.supabase_client import (
    create_payment,
    get_payment_by_checkout_id,
    get_payment_by_id,
    update_payment
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# ENV CONFIG (SAFE + CLEAN)
# ─────────────────────────────────────────────

MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "").strip()
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "").strip()
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "").strip()
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "4095377").strip()
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "").strip()

# IMPORTANT FIX (your issue)
MPESA_ENV = os.getenv("MPESA_ENV", "production").lower().strip()

BASE_URL = (
    "https://sandbox.safaricom.co.ke"
    if MPESA_ENV == "sandbox"
    else "https://api.safaricom.co.ke"
)

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

_token_cache = {"token": None, "expires": None}


# ─────────────────────────────────────────────
# CONFIG VALIDATION
# ─────────────────────────────────────────────

def is_mpesa_configured() -> bool:
    return all([
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_PASSKEY,
        MPESA_SHORTCODE,
        CALLBACK_URL
    ])


# ─────────────────────────────────────────────
# TOKEN (FIXED + SAFE CACHE)
# ─────────────────────────────────────────────

def get_mpesa_token(force: bool = False) -> str:
    global _token_cache

    if (
        not force and
        _token_cache["token"] and
        _token_cache["expires"] and
        datetime.utcnow() < _token_cache["expires"]
    ):
        return _token_cache["token"]

    auth = base64.b64encode(
        f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()
    ).decode()

    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    res = requests.get(
        url,
        headers={"Authorization": f"Basic {auth}"},
        timeout=REQUEST_TIMEOUT
    )

    if res.status_code != 200:
        raise Exception(f"M-Pesa token error: {res.text}")

    token = res.json().get("access_token")

    _token_cache = {
        "token": token,
        "expires": datetime.utcnow() + timedelta(seconds=3500)
    }

    return token


# ─────────────────────────────────────────────
# PHONE NORMALIZER (CLEAN)
# ─────────────────────────────────────────────

def normalize_phone(phone: str) -> str:
    phone = "".join(c for c in phone if c.isdigit())

    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("7"):
        phone = "254" + phone
    elif phone.startswith("254"):
        pass

    if len(phone) != 12:
        raise ValueError(f"Invalid phone number: {phone}")

    return phone


# ─────────────────────────────────────────────
# STK PUSH (FIXED + STABLE)
# ─────────────────────────────────────────────

def initiate_stk_push(
    phone: str,
    amount: float,
    payment_id: str,
    reference: str = "AUTO-V",
    user_id: Optional[str] = None
) -> Dict[str, Any]:

    if not is_mpesa_configured():
        raise Exception("M-Pesa environment not configured")

    token = get_mpesa_token()
    phone = normalize_phone(phone)

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()
    ).decode()

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(round(amount)),
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": reference or payment_id[:8],
        "TransactionDesc": "AUTO-V Payment"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"

    for attempt in range(MAX_RETRIES):
        try:
            res = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            data = res.json()

            if res.status_code in [200, 201] and data.get("ResponseCode") == "0":
                return {
                    "checkout_request_id": data.get("CheckoutRequestID"),
                    "merchant_request_id": data.get("MerchantRequestID"),
                    "response": data
                }

            if attempt < MAX_RETRIES - 1:
                continue

            raise Exception(data.get("errorMessage", "STK Push failed"))

        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            continue


# ─────────────────────────────────────────────
# CALLBACK HANDLER (FIXED SAFE DB FLOW)
# ─────────────────────────────────────────────

def handle_mpesa_callback(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        stk = data.get("Body", {}).get("stkCallback", {})

        checkout_id = stk.get("CheckoutRequestID")
        result_code = str(stk.get("ResultCode"))
        result_desc = stk.get("ResultDesc", "")

        if not checkout_id:
            return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}

        payment = get_payment_by_checkout_id(checkout_id)

        if not payment:
            return {"ResultCode": 1, "ResultDesc": "Payment not found"}

        payment_id = payment["id"]

        # SUCCESS PAYMENT
        if result_code == "0":
            receipt = None
            amount = None
            phone = None

            metadata = stk.get("CallbackMetadata", {}).get("Item", [])

            for item in metadata:
                if item.get("Name") == "MpesaReceiptNumber":
                    receipt = item.get("Value")
                elif item.get("Name") == "Amount":
                    amount = item.get("Value")
                elif item.get("Name") == "PhoneNumber":
                    phone = item.get("Value")

            update_payment(payment_id, {
                "status": "completed",
                "mpesa_code": receipt,
                "amount": amount,
                "mpesa_phone": phone,
                "paid_at": datetime.utcnow().isoformat()
            })

        # CANCELLED
        elif result_code in ["1032", "1037"]:
            update_payment(payment_id, {
                "status": "cancelled",
                "mpesa_result_desc": result_desc
            })

        # FAILED
        else:
            update_payment(payment_id, {
                "status": "failed",
                "mpesa_result_desc": result_desc,
                "mpesa_result_code": result_code
            })

        return {"ResultCode": 0, "ResultDesc": "OK"}

    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        return {"ResultCode": 1, "ResultDesc": "System error"}


# ─────────────────────────────────────────────
# STATUS QUERY
# ─────────────────────────────────────────────

def query_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    token = get_mpesa_token()

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()
    ).decode()

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id
    }

    res = requests.post(
        f"{BASE_URL}/mpesa/stkpushquery/v1/query",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=REQUEST_TIMEOUT
    )

    return res.json()


# ─────────────────────────────────────────────
# AUTO CONFIRM (ADDED FOR ROUTES)
# ─────────────────────────────────────────────

def auto_confirm_payment(payment_id: str) -> Dict[str, Any]:
    """
    Automatically confirm a payment by checking its status with M-Pesa.
    """
    payment = get_payment_by_id(payment_id)
    if not payment:
        raise ValueError(f"Payment {payment_id} not found")
    
    checkout_id = payment.get("checkout_request_id")
    if not checkout_id:
        raise ValueError(f"No checkout ID found for payment {payment_id}")
    
    # Query M-Pesa for status
    status = query_payment_status(checkout_id)
    
    result_code = status.get("ResultCode")
    
    if result_code == "0":
        update_payment(payment_id, {
            "status": "completed",
            "mpesa_result": status
        })
        return {"status": "completed", "mpesa_status": status}
    else:
        update_payment(payment_id, {
            "status": "pending",
            "mpesa_result": status
        })
        return {"status": "pending", "mpesa_status": status}


# ─────────────────────────────────────────────
# EXPORTS
# ─────────────────────────────────────────────

__all__ = [
    "initiate_stk_push",
    "handle_mpesa_callback",
    "query_payment_status",
    "normalize_phone",
    "get_mpesa_token",
    "is_mpesa_configured",
    "auto_confirm_payment"
]
