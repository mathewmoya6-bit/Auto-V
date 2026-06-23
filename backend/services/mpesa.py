# services/mpesa.py - Production Ready v4

import os
import base64
import logging
import requests
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ─── CONFIG ─────────────────────────────────────────────

MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "").strip()
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "").strip()
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "").strip()
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "4095377").strip()
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "").strip()

MPESA_ENV = os.getenv("MPESA_ENV", "production").lower().strip()

BASE_URL = (
    "https://sandbox.safaricom.co.ke"
    if MPESA_ENV == "sandbox"
    else "https://api.safaricom.co.ke"
)

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
_token_cache = {"token": None, "expires": None}


# ─── VALIDATION ─────────────────────────────────────────

def is_mpesa_configured() -> bool:
    return all([
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_PASSKEY,
        MPESA_SHORTCODE,
        CALLBACK_URL
    ])


# ─── TOKEN ──────────────────────────────────────────────

def get_mpesa_token(force: bool = False) -> str:
    global _token_cache

    if not force and _token_cache["token"] and _token_cache["expires"] and datetime.utcnow() < _token_cache["expires"]:
        return _token_cache["token"]

    auth = base64.b64encode(
        f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()
    ).decode()

    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    res = requests.get(url, headers={"Authorization": f"Basic {auth}"}, timeout=REQUEST_TIMEOUT)

    if res.status_code != 200:
        raise Exception(f"Token error: {res.text}")

    token = res.json().get("access_token")

    _token_cache = {
        "token": token,
        "expires": datetime.utcnow() + timedelta(seconds=3500)
    }

    return token


# ─── PHONE NORMALIZER ───────────────────────────────────

def normalize_phone(phone: str) -> str:
    phone = ''.join(c for c in phone if c.isdigit())

    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("7"):
        phone = "254" + phone

    if not phone.startswith("254") or len(phone) != 12:
        raise ValueError("Invalid phone number")

    return phone


# ─── STK PUSH ───────────────────────────────────────────

def initiate_stk_push(phone: str, amount: float, payment_id: str, reference: str = "AUTO-V", user_id=None):

    if not is_mpesa_configured():
        raise Exception("M-Pesa not configured")

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
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": reference,
        "TransactionDesc": "AUTO-V Payment"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"

    for attempt in range(MAX_RETRIES):
        res = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)

        if res.status_code in [200, 201]:
            data = res.json()

            if data.get("ResponseCode") != "0":
                raise Exception(data.get("ResponseDescription"))

            return {
                "checkout_request_id": data.get("CheckoutRequestID"),
                "merchant_request_id": data.get("MerchantRequestID"),
                "response": data
            }

        time.sleep(2 ** attempt)

    raise Exception("STK Push failed after retries")


# ─── CALLBACK ───────────────────────────────────────────

def handle_mpesa_callback(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        stk = data.get("Body", {}).get("stkCallback", {})

        checkout_id = stk.get("CheckoutRequestID")
        result_code = str(stk.get("ResultCode"))

        from services.supabase_client import (
            get_payment_by_checkout_id,
            update_payment
        )

        payment = get_payment_by_checkout_id(checkout_id)

        if not payment:
            return {"ResultCode": 1, "ResultDesc": "Not found"}

        payment_id = payment["id"]

        if result_code == "0":
            metadata = stk.get("CallbackMetadata", {}) or {}
            items = metadata.get("Item", [])

            receipt = None

            for i in items:
                if i.get("Name") == "MpesaReceiptNumber":
                    receipt = i.get("Value")

            update_payment(payment_id, {
                "status": "completed",
                "mpesa_code": receipt,
                "paid_at": datetime.utcnow().isoformat()
            })

        return {"ResultCode": 0, "ResultDesc": "OK"}

    except Exception as e:
        logger.error(e)
        return {"ResultCode": 1, "ResultDesc": "Error"}
