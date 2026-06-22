# services/mpesa.py - M-Pesa Service (Production Ready v2)

import os
import base64
import logging
import requests
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# ─── CONFIG ────────────────────────────────────────────────
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', '')
MPESA_ENV = os.getenv('MPESA_ENV', 'production').lower()

BASE_URL = (
    'https://sandbox.safaricom.co.ke'
    if MPESA_ENV == 'production'
    else 'https://api.safaricom.co.ke'
)

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
_token_cache = {'token': None, 'expires_at': None}


# ─── SAFETY CHECK ──────────────────────────────────────────
def is_mpesa_configured() -> bool:
    required = [
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_PASSKEY,
        MPESA_SHORTCODE,
        CALLBACK_URL
    ]

    if not all(required):
        missing = [k for k, v in {
            'MPESA_CONSUMER_KEY': MPESA_CONSUMER_KEY,
            'MPESA_CONSUMER_SECRET': MPESA_CONSUMER_SECRET,
            'MPESA_PASSKEY': MPESA_PASSKEY,
            'MPESA_SHORTCODE': MPESA_SHORTCODE,
            'MPESA_CALLBACK_URL': CALLBACK_URL
        }.items() if not v]

        logger.error(f"❌ Missing M-Pesa config: {', '.join(missing)}")
        return False

    if MPESA_ENV == 'production':
        if len(MPESA_SHORTCODE) != 7:
            logger.error("❌ Production shortcode must be 7 digits")
            return False
        if not CALLBACK_URL.startswith("https://"):
            logger.error("❌ Callback URL must use HTTPS")
            return False

    return True


# ─── PHONE NORMALIZER (FIXED) ──────────────────────────────
def normalize_phone(phone: str) -> str:
    if not phone:
        raise ValueError("Phone number is required")

    phone = phone.strip()

    if phone.startswith("+254"):
        phone = phone[1:]

    phone = ''.join(c for c in phone if c.isdigit())

    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        phone = "254" + phone

    if not phone.startswith("254") or len(phone) != 12:
        raise ValueError(f"Invalid phone format: {phone}")

    return phone


# ─── TOKEN ──────────────────────────────────────────────────
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

    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(
                url,
                headers={"Authorization": f"Basic {auth}"},
                timeout=REQUEST_TIMEOUT
            )

            data = res.json()
            token = data.get("access_token")

            if not token:
                raise Exception("Invalid token response")

            _token_cache = {
                "token": token,
                "expires_at": datetime.now() + timedelta(seconds=3500)
            }

            return token

        except Exception as e:
            logger.error(f"Token error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise


# ─── STK PUSH ──────────────────────────────────────────────
def initiate_stk_push(
    phone: str,
    amount: float,
    payment_id: str,
    service: str = "AUTO-V",
    reference: Optional[str] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:

    if not is_mpesa_configured():
        raise Exception("M-Pesa not configured")

    if amount < 1:
        raise ValueError("Minimum amount is 1 KES")

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
        "AccountReference": reference or f"AUTO-{payment_id[:8]}",
        "TransactionDesc": service[:30]
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"

    for attempt in range(MAX_RETRIES):
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            data = res.json()

            if data.get("ResponseCode") != "0":
                raise Exception(data.get("ResponseDescription"))

            checkout_id = data.get("CheckoutRequestID")

            # ─── SAVE PAYMENT ───────────────────────────────
            try:
                from services.supabase_client import create_payment

                payment_uuid = str(uuid.uuid4())

                create_payment({
                    "id": payment_uuid,
                    "payment_id": payment_id,
                    "user_id": user_id,
                    "request_id": request_id,
                    "amount": amount,
                    "phone": phone,
                    "mpesa_phone": phone,
                    "checkout_request_id": checkout_id,
                    "merchant_request_id": data.get("MerchantRequestID"),
                    "payment_method": "mpesa",
                    "status": "pending"
                })

            except Exception as db_err:
                logger.warning(f"DB save failed: {db_err}")

            return {
                "success": True,
                "payment_id": payment_id,
                "checkout_request_id": checkout_id,
                "merchant_request_id": data.get("MerchantRequestID")
            }

        except Exception as e:
            logger.error(f"STK error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise


# ─── CALLBACK HANDLER ──────────────────────────────────────
def handle_mpesa_callback(callback_data: Dict[str, Any], client_ip=None):

    stk = callback_data.get("Body", {}).get("stkCallback", {})

    checkout_id = stk.get("CheckoutRequestID")
    result_code = str(stk.get("ResultCode"))

    from services.supabase_client import get_payment_by_checkout_id, update_payment

    payment = get_payment_by_checkout_id(checkout_id)

    if not payment:
        return {"ResultCode": 1, "ResultDesc": "Not found"}

    payment_uuid = payment["id"]

    if payment.get("status") == "completed":
        return {"ResultCode": 0, "ResultDesc": "Already processed"}

    if result_code == "0":
        metadata = stk.get("CallbackMetadata", {}).get("Item", [])

        receipt = None
        amount = None
        phone = None

        for i in metadata:
            if i["Name"] == "MpesaReceiptNumber":
                receipt = i["Value"]
            if i["Name"] == "Amount":
                amount = i["Value"]
            if i["Name"] == "PhoneNumber":
                phone = i["Value"]

        update_payment(payment_uuid, {
            "status": "completed",
            "mpesa_code": receipt,
            "transaction_id": receipt,
            "paid_at": datetime.now().isoformat(),
            "mpesa_phone": phone
        })

    elif result_code in ["1032", "1037"]:
        update_payment(payment_uuid, {
            "status": "cancelled"
        })

    else:
        update_payment(payment_uuid, {
            "status": "failed"
        })

    return {"ResultCode": 0, "ResultDesc": "Success"}


# ─── QUERY STATUS ───────────────────────────────────────────
def query_payment_status(checkout_request_id: str):

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
        headers={"Authorization": f"Bearer {token}"}
    )

    return res.json()
# ─── VERIFY PAYMENT ──────────────────────────────────────────

def verify_payment_with_mpesa(checkout_request_id: str):
    """
    Verify payment directly with Safaricom using STK Query API.
    """

    try:
        result = query_payment_status(checkout_request_id)

        result_code = str(result.get("ResultCode", ""))

        if result_code == "0":
            return {
                "verified": True,
                "status": "completed",
                "receipt": result.get("MpesaReceiptNumber"),
                "amount": result.get("Amount"),
                "phone": result.get("PhoneNumber"),
                "result_code": result_code,
                "result_desc": result.get("ResultDesc")
            }

        if result_code in ["1032", "1037"]:
            return {
                "verified": False,
                "status": "cancelled",
                "result_code": result_code,
                "result_desc": result.get("ResultDesc")
            }

        return {
            "verified": False,
            "status": "pending",
            "result_code": result_code,
            "result_desc": result.get("ResultDesc")
        }

    except Exception as e:
        logger.error(f"Verify payment error: {e}")

        return {
            "verified": False,
            "status": "error",
            "result_desc": str(e)
        }


# ─── AUTO CONFIRM PAYMENT ────────────────────────────────────

def auto_confirm_payment(payment_uuid: str):
    """
    Auto-confirm payment using checkout_request_id.
    """

    try:
        from services.supabase_client import (
            get_payment_by_id,
            update_payment
        )

        payment = get_payment_by_id(payment_uuid)

        if not payment:
            return {
                "success": False,
                "error": "Payment not found"
            }

        checkout_request_id = payment.get("checkout_request_id")

        if not checkout_request_id:
            return {
                "success": False,
                "error": "CheckoutRequestID missing"
            }

        verification = verify_payment_with_mpesa(
            checkout_request_id
        )

        if verification.get("verified"):

            receipt = verification.get("receipt")

            update_result = update_payment(
                payment_uuid,
                {
                    "status": "completed",
                    "mpesa_code": receipt,
                    "transaction_id": receipt,
                    "mpesa_result_code": "0",
                    "mpesa_result_desc": "Payment confirmed",
                    "paid_at": datetime.now().isoformat()
                }
            )

            return {
                "success": True,
                "status": "completed",
                "receipt": receipt,
                "payment": update_result.get("data")
            }

        return {
            "success": False,
            "status": verification.get("status"),
            "result_code": verification.get("result_code"),
            "result_desc": verification.get("result_desc")
        }

    except Exception as e:
        logger.error(f"Auto confirm payment error: {e}")

        return {
            "success": False,
            "error": str(e)
        }

# ─── EXPORTS ────────────────────────────────────────────────
__all__ = [
    "initiate_stk_push",
    "handle_mpesa_callback",
    "query_payment_status",
    "get_mpesa_token",
    "normalize_phone",
    "is_mpesa_configured"
]
]
