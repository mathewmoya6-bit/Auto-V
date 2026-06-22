# services/mpesa.py - FINAL PRODUCTION STABLE

import os
import base64
import logging
import requests
import time
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─── CONFIG ─────────────────────────────────────────────
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "4095377")
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "")
MPESA_ENV = os.getenv("MPESA_ENV", "production")

BASE_URL = (
    "https://sandbox.safaricom.co.ke"
    if MPESA_ENV == "sandbox"
    else "https://api.safaricom.co.ke"
)

_token_cache = {"token": None, "expires": None}


# ─── CONFIG CHECK ───────────────────────────────────────
def is_mpesa_configured():
    return all([
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_PASSKEY,
        MPESA_SHORTCODE,
        CALLBACK_URL
    ])


# ─── TOKEN ──────────────────────────────────────────────
def get_mpesa_token():
    global _token_cache

    if _token_cache["token"] and _token_cache["expires"] > datetime.now():
        return _token_cache["token"]

    auth = base64.b64encode(
        f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()
    ).decode()

    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    res = requests.get(url, headers={"Authorization": f"Basic {auth}"})
    token = res.json().get("access_token")

    _token_cache = {
        "token": token,
        "expires": datetime.now() + timedelta(seconds=3500)
    }

    return token


# ─── PHONE NORMALIZER ───────────────────────────────────
def normalize_phone(phone):
    phone = phone.strip().replace("+", "")

    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("7"):
        phone = "254" + phone

    if len(phone) != 12:
        raise ValueError("Invalid phone number")

    return phone


# ─── STK PUSH ───────────────────────────────────────────
def initiate_stk_push(phone, amount, payment_id, reference="AUTO-V"):

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
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": reference,
        "TransactionDesc": "AUTO-V Payment"
    }

    headers = {"Authorization": f"Bearer {token}"}

    url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"

    res = requests.post(url, json=payload, headers=headers)
    data = res.json()

    if data.get("ResponseCode") != "0":
        raise Exception(data.get("errorMessage"))

    return {
        "checkout_request_id": data.get("CheckoutRequestID"),
        "merchant_request_id": data.get("MerchantRequestID")
    }


# ─── CALLBACK ───────────────────────────────────────────
def handle_mpesa_callback(data):

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

    if result_code == "0":
        update_payment(payment["id"], {
            "status": "completed",
            "mpesa_code": "SUCCESS",
            "paid_at": datetime.now().isoformat()
        })
    else:
        update_payment(payment["id"], {
            "status": "failed"
        })

    return {"ResultCode": 0, "ResultDesc": "Success"}


# ─── QUERY ──────────────────────────────────────────────
def query_payment_status(checkout_id):
    token = get_mpesa_token()

    url = f"{BASE_URL}/mpesa/stkpushquery/v1/query"

    res = requests.post(url, json={
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": "",
        "Timestamp": datetime.now().strftime("%Y%m%d%H%M%S"),
        "CheckoutRequestID": checkout_id
    }, headers={"Authorization": f"Bearer {token}"})

    return res.json()


# ─── EXPORTS ────────────────────────────────────────────
__all__ = [
    "initiate_stk_push",
    "handle_mpesa_callback",
    "query_payment_status",
    "is_mpesa_configured",
    "normalize_phone",
    "get_mpesa_token"
]
