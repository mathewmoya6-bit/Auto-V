# services/mpesa.py – FINTECH M-PESA ENGINE (HARDENED)

import os
import base64
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from dotenv import load_dotenv
from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
load_dotenv()

# ─── CONFIG ────────────────────────────────────────────────
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', '')
MPESA_ENV = os.getenv('MPESA_ENV', 'sandbox').lower()

BASE_URL = (
    'https://sandbox.safaricom.co.ke'
    if MPESA_ENV == 'sandbox'
    else 'https://api.safaricom.co.ke'
)

REQUEST_TIMEOUT = 15
_token_cache = {'token': None, 'expires_at': None}


# ─── SAFETY CHECK ──────────────────────────────────────────
def is_mpesa_configured() -> bool:
    return all([
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_PASSKEY,
        MPESA_SHORTCODE,
        CALLBACK_URL
    ])


# ─── PHONE NORMALIZER (HARDENED) ───────────────────────────
def normalize_phone(phone: str) -> str:
    if not phone:
        raise ValueError("Phone number required")

    phone = ''.join(c for c in phone if c.isdigit())

    if phone.startswith("0"):
        phone = "254" + phone[1:]

    if phone.startswith("7") and len(phone) == 9:
        phone = "254" + phone

    if not phone.startswith("254") or len(phone) != 12:
        raise ValueError(f"Invalid phone format: {phone}")

    return phone


# ─── TOKEN (CACHED + SAFE) ────────────────────────────────
def get_mpesa_token(force: bool = False) -> str:
    global _token_cache

    if (
        not force
        and _token_cache["token"]
        and _token_cache["expires_at"]
        and datetime.now() < _token_cache["expires_at"]
    ):
        return _token_cache["token"]

    auth = base64.b64encode(
        f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()
    ).decode()

    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    for attempt in range(3):
        try:
            res = requests.get(
                url,
                headers={"Authorization": f"Basic {auth}"},
                timeout=REQUEST_TIMEOUT
            )
            res.raise_for_status()
            data = res.json()

            token = data["access_token"]

            _token_cache = {
                "token": token,
                "expires_at": datetime.now() + timedelta(seconds=3500)
            }

            return token

        except Exception as e:
            logger.warning(f"Token attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)

    raise Exception("Failed to get M-Pesa token")


# ─── STK PUSH (FINTECH HARDENED) ───────────────────────────
def initiate_stk_push(phone: str, amount: float, payment_id: str, service: str = "AUTO-V") -> Dict[str, Any]:
    if not is_mpesa_configured():
        raise Exception("M-Pesa not configured")

    token = get_mpesa_token()
    phone = normalize_phone(phone)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
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
        "AccountReference": f"AUTO-{payment_id[:6]}",
        "TransactionDesc": service
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"

    res = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    data = res.json()

    if data.get("ResponseCode") != "0":
        raise Exception(data.get("errorMessage") or data.get("ResponseDescription"))

    # IMPORTANT: return CheckoutRequestID
    return {
        "checkout_request_id": data.get("CheckoutRequestID"),
        "merchant_request_id": data.get("MerchantRequestID"),
        "raw": data
    }


# ─── STATUS QUERY ──────────────────────────────────────────
def query_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    token = get_mpesa_token()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
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
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        timeout=REQUEST_TIMEOUT
    )

    return res.json()


# ─── CALLBACK (BULLETPROOF ENGINE) ─────────────────────────
def handle_mpesa_callback(callback_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        stk = callback_data.get("Body", {}).get("stkCallback", {})

        checkout_id = stk.get("CheckoutRequestID")
        result_code = str(stk.get("ResultCode"))
        result_desc = stk.get("ResultDesc")
        transaction_id = stk.get("CallbackMetadata", {}).get("Item", [{}])[1].get("Value")

        if not checkout_id:
            return {"ResultCode": 1, "ResultDesc": "Missing checkout ID"}

        supabase = get_supabase()

        # 🔥 FIXED FIELD NAME
        payment = supabase.table("payments") \
            .select("*") \
            .eq("checkout_request_id", checkout_id) \
            .execute()

        if not payment.data:
            return {"ResultCode": 1, "ResultDesc": "Payment not found"}

        payment = payment.data[0]
        payment_id = payment["id"]

        # 🧠 IDENTITY PROTECTION
        if payment["status"] == "completed":
            return {"ResultCode": 0, "ResultDesc": "Already processed"}

        # ─── STATUS UPDATE ────────────────────────────────
        if result_code == "0":
            update = {
                "status": "completed",
                "transaction_id": transaction_id,
                "completed_at": datetime.now().isoformat(),
                "mpesa_result_desc": result_desc
            }
        else:
            update = {
                "status": "failed",
                "mpesa_result_desc": result_desc,
                "mpesa_result_code": result_code
            }

        supabase.table("payments").update(update).eq("id", payment_id).execute()

        return {"ResultCode": 0, "ResultDesc": "Success"}

    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        return {"ResultCode": 0, "ResultDesc": "Error handled safely"}
