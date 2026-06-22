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

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
_token_cache = {"token": None, "expires": None}


# ─── CONFIG CHECK ───────────────────────────────────────
def is_mpesa_configured():
    """Check if all M-Pesa config is present."""
    return all([
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_PASSKEY,
        MPESA_SHORTCODE,
        CALLBACK_URL
    ])


# ─── TOKEN ──────────────────────────────────────────────
def get_mpesa_token(force=False):
    """Get M-Pesa access token with caching."""
    global _token_cache

    if (
        not force
        and _token_cache["token"]
        and _token_cache["expires"]
        and datetime.now() < _token_cache["expires"]
    ):
        return _token_cache["token"]

    auth = base64.b64encode(
        f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()
    ).decode()

    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(url, headers={"Authorization": f"Basic {auth}"}, timeout=REQUEST_TIMEOUT)
            
            if res.status_code != 200:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"Token request failed: {res.status_code}")

            data = res.json()
            token = data.get("access_token")
            
            if not token:
                raise Exception("No access_token in response")

            _token_cache = {
                "token": token,
                "expires": datetime.now() + timedelta(seconds=3500)
            }

            return token

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise


# ─── PHONE NORMALIZER ───────────────────────────────────
def normalize_phone(phone):
    """Normalize phone number to 254XXXXXXXXX format."""
    if not phone:
        raise ValueError("Phone number is required")

    phone = ''.join(c for c in phone if c.isdigit())

    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        phone = "254" + phone
    elif phone.startswith("+254"):
        phone = phone[1:]

    if not phone.startswith("254") or len(phone) != 12:
        raise ValueError(f"Invalid phone format: {phone}")

    return phone


# ─── STK PUSH ───────────────────────────────────────────
def initiate_stk_push(phone, amount, payment_id, reference="AUTO-V", user_id=None, request_id=None):
    """Initiate STK Push to customer's phone."""
    
    if not is_mpesa_configured():
        raise Exception("M-Pesa not configured")

    if amount <= 0:
        raise ValueError("Amount must be greater than 0")
    
    if amount < 1:
        raise ValueError("Minimum payment is 1 KES")

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
        "AccountReference": reference or f"AUTO-{payment_id[:8].upper()}",
        "TransactionDesc": "AUTO-V Payment"
    }

    logger.info(f"📤 Initiating STK Push for payment {payment_id}")
    logger.info(f"📱 Phone: {phone}, Amount: {amount}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"

    for attempt in range(MAX_RETRIES):
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if res.status_code != 200:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"STK Push failed: {res.status_code}")

            data = res.json()
            logger.info(f"📥 STK Push response: {data}")

            if data.get("ResponseCode") != "0":
                error_msg = data.get("ResponseDescription", "Unknown error")
                raise Exception(f"M-Pesa error: {error_msg}")

            checkout_id = data.get("CheckoutRequestID")
            if not checkout_id:
                raise Exception("No CheckoutRequestID returned")

            # ─── Create Payment Record ──────────────────────────────────
            try:
                from services.supabase_client import create_payment
                
                # Generate proper UUID for the primary key
                payment_uuid = str(uuid.uuid4())
                
                payment_data = {
                    'id': payment_uuid,
                    'payment_id': payment_id,
                    'user_id': user_id,
                    'request_id': request_id,
                    'amount': amount,
                    'phone': phone,
                    'mpesa_phone': phone,
                    'merchant_request_id': data.get("MerchantRequestID"),
                    'checkout_request_id': checkout_id,
                    'payment_method': 'mpesa',
                    'status': 'pending'
                }
                
                create_result = create_payment(payment_data)
                if not create_result.get('success'):
                    logger.warning(f"⚠️ Could not create payment record: {create_result.get('error')}")
            except Exception as db_err:
                logger.warning(f"⚠️ Database error: {db_err}")

            return {
                "checkout_request_id": checkout_id,
                "merchant_request_id": data.get("MerchantRequestID"),
                "response_code": data.get("ResponseCode"),
                "response_description": data.get("ResponseDescription")
            }

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise


# ─── CALLBACK ───────────────────────────────────────────
def handle_mpesa_callback(data):
    """Handle M-Pesa callback and update payment status."""
    try:
        stk = data.get("Body", {}).get("stkCallback", {})
        if not stk:
            return {"ResultCode": 1, "ResultDesc": "Missing stkCallback"}

        checkout_id = stk.get("CheckoutRequestID")
        result_code = str(stk.get("ResultCode"))
        result_desc = stk.get("ResultDesc", "Unknown")

        if not checkout_id:
            return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}

        logger.info(f"📊 Callback: CheckoutID={checkout_id}, ResultCode={result_code}")

        from services.supabase_client import get_payment_by_checkout_id, update_payment

        payment = get_payment_by_checkout_id(checkout_id)

        if not payment:
            logger.error(f"❌ Payment not found for CheckoutID: {checkout_id}")
            return {"ResultCode": 1, "ResultDesc": "Payment not found"}

        payment_uuid = payment.get("id")
        payment_id = payment.get("payment_id")

        if payment.get("status") == "completed":
            logger.info(f"ℹ️ Payment {payment_id} already completed")
            return {"ResultCode": 0, "ResultDesc": "Already processed"}

        # Extract transaction details
        transaction_id = None
        amount = None
        phone = None

        metadata = stk.get("CallbackMetadata")
        if metadata:
            items = metadata.get("Item", [])
            for item in items:
                name = item.get("Name")
                value = item.get("Value")
                if name == "MpesaReceiptNumber":
                    transaction_id = value
                elif name == "Amount":
                    amount = value
                elif name == "PhoneNumber":
                    phone = value

        if result_code == "0" and transaction_id:
            update_data = {
                "status": "completed",
                "mpesa_code": transaction_id,
                "transaction_id": transaction_id,
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction completed",
                "paid_at": datetime.now().isoformat()
            }
            if amount:
                update_data["amount"] = amount
            if phone:
                update_data["mpesa_phone"] = phone

            result = update_payment(payment_uuid, update_data)
            if result.get('success'):
                logger.info(f"✅ Payment {payment_id} completed. Receipt: {transaction_id}")
                return {"ResultCode": 0, "ResultDesc": "Success"}
            else:
                return {"ResultCode": 1, "ResultDesc": "Update failed"}

        elif result_code in ["1037", "1032"]:
            update_payment(payment_uuid, {
                "status": "cancelled",
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction cancelled"
            })
            logger.warning(f"⚠️ Payment {payment_id} cancelled")
            return {"ResultCode": 0, "ResultDesc": "Success"}

        else:
            update_payment(payment_uuid, {
                "status": "failed",
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction failed"
            })
            logger.warning(f"❌ Payment {payment_id} failed: {result_desc}")
            return {"ResultCode": 0, "ResultDesc": "Success"}

    except Exception as e:
        logger.error(f"❌ Callback error: {e}", exc_info=True)
        return {"ResultCode": 1, "ResultDesc": "System error"}


# ─── EXPORTS ────────────────────────────────────────────
__all__ = [
    "initiate_stk_push",
    "handle_mpesa_callback",
    "is_mpesa_configured",
    "normalize_phone",
    "get_mpesa_token"
]
