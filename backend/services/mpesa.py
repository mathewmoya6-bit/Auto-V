# services/mpesa.py - FIXED VERSION (Production Ready)

import os
import base64
import logging
import requests
import time
import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
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
MPESA_ENV = os.getenv('MPESA_ENV', 'production').lower()  # ← Default to production

# ─── BASE URL ──────────────────────────────────────────────
BASE_URL = (
    'https://sandbox.safaricom.co.ke'
    if MPESA_ENV == 'sandbox'
    else 'https://api.safaricom.co.ke'  # Production
)

REQUEST_TIMEOUT = 30  # Increased for production
MAX_RETRIES = 3
_token_cache = {'token': None, 'expires_at': None}


# ─── SAFARICOM IP VERIFICATION ─────────────────────────────
SAFARICOM_IPS = [
    '196.201.214.0/24',
    '196.201.215.0/24',
    '196.201.216.0/24',
    '196.201.217.0/24',
    '196.201.218.0/24',
    '196.201.219.0/24',
    '196.201.220.0/24',
    '196.201.221.0/24',
]

def verify_safaricom_ip(ip: str) -> bool:
    """
    Verify if IP belongs to Safaricom's production ranges.
    Returns True if valid, False otherwise.
    """
    if not ip:
        logger.warning("⚠️ No IP provided for verification")
        return False
    
    # In production, strictly verify
    if MPESA_ENV == 'production':
        try:
            import ipaddress
            ip_addr = ipaddress.ip_address(ip)
            for cidr in SAFARICOM_IPS:
                if ip_addr in ipaddress.ip_network(cidr):
                    logger.info(f"✅ IP {ip} verified as Safaricom")
                    return True
            logger.warning(f"❌ IP {ip} not in Safaricom ranges")
            return False
        except Exception as e:
            logger.error(f"❌ IP verification error: {e}")
            return False
    else:
        # In sandbox, allow localhost for testing
        if ip in ['127.0.0.1', 'localhost']:
            return True
        return True  # Allow all in sandbox for testing


# ─── SAFETY CHECK ──────────────────────────────────────────
def is_mpesa_configured() -> bool:
    """Check if all M-Pesa configuration is present."""
    required = [
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_PASSKEY,
        MPESA_SHORTCODE,
        CALLBACK_URL
    ]
    
    if not all(required):
        missing = []
        if not MPESA_CONSUMER_KEY: missing.append('MPESA_CONSUMER_KEY')
        if not MPESA_CONSUMER_SECRET: missing.append('MPESA_CONSUMER_SECRET')
        if not MPESA_PASSKEY: missing.append('MPESA_PASSKEY')
        if not MPESA_SHORTCODE: missing.append('MPESA_SHORTCODE')
        if not CALLBACK_URL: missing.append('MPESA_CALLBACK_URL')
        logger.error(f"❌ Missing M-Pesa config: {', '.join(missing)}")
        return False
    
    # Validate shortcode
    if MPESA_ENV == 'production' and len(MPESA_SHORTCODE) != 7:
        logger.error(f"❌ Production shortcode must be 7 digits: {MPESA_SHORTCODE}")
        return False
    
    # Validate callback URL
    if MPESA_ENV == 'production' and not CALLBACK_URL.startswith('https://'):
        logger.error("❌ Production callback must use HTTPS")
        return False
    
    logger.info("✅ M-Pesa configuration validated")
    return True


# ─── PHONE NORMALIZER ──────────────────────────────────────
def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to 254XXXXXXXXX format.
    """
    if not phone:
        raise ValueError("Phone number is required")

    # Remove all non-digit characters
    phone = ''.join(c for c in phone if c.isdigit())

    # Remove leading 0
    if phone.startswith("0"):
        phone = "254" + phone[1:]

    # Add 254 if starting with 7
    if phone.startswith("7") and len(phone) == 9:
        phone = "254" + phone

    # Validate final format
    if not phone.startswith("254") or len(phone) != 12:
        raise ValueError(f"Invalid phone format: {phone}")

    return phone


# ─── TOKEN ──────────────────────────────────────────────────
def get_mpesa_token(force: bool = False) -> str:
    """
    Get M-Pesa access token with caching.
    """
    global _token_cache

    # Check cache
    if (
        not force
        and _token_cache["token"]
        and _token_cache["expires_at"]
        and datetime.now() < _token_cache["expires_at"]
    ):
        logger.debug("✅ Using cached token")
        return _token_cache["token"]

    logger.info("🔄 Acquiring new M-Pesa token")

    auth = base64.b64encode(
        f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()
    ).decode()

    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    for attempt in range(MAX_RETRIES):
        try:
            # ─── REMOVED proxy parameter ──────────────────────────
            res = requests.get(
                url,
                headers={"Authorization": f"Basic {auth}"},
                timeout=REQUEST_TIMEOUT
            )
            
            if res.status_code != 200:
                logger.error(f"❌ Token request failed: {res.status_code}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"Token request failed: {res.status_code}")

            data = res.json()
            token = data.get("access_token")
            
            if not token:
                logger.error(f"❌ No access_token in response: {data}")
                raise Exception("Invalid token response")

            _token_cache = {
                "token": token,
                "expires_at": datetime.now() + timedelta(seconds=3500)
            }

            logger.info("✅ M-Pesa token acquired")
            return token

        except requests.exceptions.Timeout:
            logger.error(f"❌ Token timeout (attempt {attempt+1})")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise Exception("Token request timeout")
            
        except Exception as e:
            logger.error(f"❌ Token error: {e}")
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
    reference: Optional[str] = None
) -> Dict[str, Any]:
    """
    Initiate STK Push to customer's phone.
    Returns M-Pesa response.
    """
    if not is_mpesa_configured():
        raise Exception("M-Pesa is not configured")

    # Validate amount
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

    # ─── Build payload ──────────────────────────────────────────
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
        "TransactionDesc": service[:36]  # Max 36 characters
    }

    logger.info(f"📤 Initiating STK Push for payment {payment_id}")
    logger.info(f"📱 Phone: {phone}, Amount: {amount}, Shortcode: {MPESA_SHORTCODE}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"

    for attempt in range(MAX_RETRIES):
        try:
            # ─── REMOVED proxy parameter ──────────────────────────
            res = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=REQUEST_TIMEOUT
            )
            
            if res.status_code != 200:
                logger.error(f"❌ STK Push failed (attempt {attempt+1}): {res.status_code}")
                logger.error(f"Response: {res.text[:500]}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"STK Push failed: {res.status_code}")

            data = res.json()
            logger.info(f"📥 STK Push response: {data}")

            # Check response code
            if data.get("ResponseCode") != "0":
                error_msg = data.get("ResponseDescription", "Unknown error")
                raise Exception(f"M-Pesa error: {error_msg}")

            checkout_id = data.get("CheckoutRequestID")
            if not checkout_id:
                raise Exception("No CheckoutRequestID returned")

            return {
                "CheckoutRequestID": checkout_id,
                "MerchantRequestID": data.get("MerchantRequestID"),
                "ResponseCode": data.get("ResponseCode"),
                "ResponseDescription": data.get("ResponseDescription")
            }

        except requests.exceptions.Timeout:
            logger.error(f"❌ STK Push timeout (attempt {attempt+1})")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise Exception("STK Push timeout")
            
        except Exception as e:
            logger.error(f"❌ STK Push error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise


# ─── STATUS QUERY ──────────────────────────────────────────
def query_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    """
    Query M-Pesa payment status.
    """
    if not checkout_request_id:
        raise ValueError("CheckoutRequestID is required")

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

    logger.info(f"🔍 Querying payment status: {checkout_request_id}")

    for attempt in range(MAX_RETRIES):
        try:
            # ─── REMOVED proxy parameter ──────────────────────────
            res = requests.post(
                f"{BASE_URL}/mpesa/stkpushquery/v1/query",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=REQUEST_TIMEOUT
            )
            
            if res.status_code != 200:
                logger.error(f"❌ Status query failed (attempt {attempt+1}): {res.status_code}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"Status query failed: {res.status_code}")

            data = res.json()
            logger.info(f"📥 Status query response: {data}")
            return data

        except Exception as e:
            logger.error(f"❌ Status query error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise


# ─── CALLBACK HANDLER ──────────────────────────────────────
def handle_mpesa_callback(callback_data: Dict[str, Any], client_ip: str = None) -> Dict[str, Any]:
    """
    Handle M-Pesa callback with proper transaction extraction.
    """
    try:
        logger.info("=" * 60)
        logger.info("📥 Processing M-Pesa callback")
        
        if not callback_data:
            logger.error("❌ No callback data")
            return {"ResultCode": 1, "ResultDesc": "No data"}

        # ─── Validate callback structure ──────────────────────────
        stk = callback_data.get("Body", {}).get("stkCallback", {})
        if not stk:
            logger.error("❌ Missing stkCallback")
            return {"ResultCode": 1, "ResultDesc": "Missing stkCallback"}

        checkout_id = stk.get("CheckoutRequestID")
        result_code = str(stk.get("ResultCode"))
        result_desc = stk.get("ResultDesc")

        logger.info(f"📊 CheckoutID: {checkout_id}, ResultCode: {result_code}")

        if not checkout_id:
            logger.error("❌ Missing CheckoutRequestID")
            return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}

        # ─── Extract transaction ID ────────────────────────────────
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
                    logger.info(f"✅ Found MpesaReceiptNumber: {value}")
                elif name == "Amount":
                    amount = value
                elif name == "PhoneNumber":
                    phone = value
        else:
            logger.warning("⚠️ No CallbackMetadata found")

        # ─── Update database ────────────────────────────────────
        supabase = get_supabase()

        # Find payment by checkout_id
        payment = supabase.table("payments") \
            .select("*") \
            .eq("checkout_request_id", checkout_id) \
            .execute()

        if not payment.data:
            logger.error(f"❌ Payment not found for CheckoutID: {checkout_id}")
            return {"ResultCode": 1, "ResultDesc": "Payment not found"}

        payment = payment.data[0]
        payment_id = payment["id"]
        logger.info(f"✅ Found payment: {payment_id}")

        # ─── Idempotency check ──────────────────────────────────
        if payment.get("status") == "completed":
            logger.info(f"ℹ️ Payment {payment_id} already completed")
            return {"ResultCode": 0, "ResultDesc": "Already processed"}

        # ─── Update status ──────────────────────────────────────
        if result_code == "0" and transaction_id:
            update = {
                "status": "completed",
                "transaction_id": transaction_id,
                "mpesa_receipt_number": transaction_id,
                "amount_paid": amount,
                "completed_at": datetime.now().isoformat(),
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction completed"
            }
            logger.info(f"✅ Payment {payment_id} completed. Receipt: {transaction_id}")
            
        elif result_code in ["1037", "1032"]:
            update = {
                "status": "cancelled",
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction cancelled"
            }
            logger.warning(f"⚠️ Payment {payment_id} cancelled")
            
        else:
            update = {
                "status": "failed",
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction failed"
            }
            logger.warning(f"❌ Payment {payment_id} failed: {result_desc}")

        result = supabase.table("payments").update(update).eq("id", payment_id).execute()
        
        if result.data:
            logger.info(f"✅ Database updated: {result.data[0].get('status')}")
            return {"ResultCode": 0, "ResultDesc": "Success"}
        else:
            logger.error("❌ Database update failed")
            return {"ResultCode": 1, "ResultDesc": "Update failed"}

    except Exception as e:
        logger.error(f"❌ Callback error: {e}", exc_info=True)
        return {"ResultCode": 1, "ResultDesc": str(e)}


# ─── SANITIZE LOG DATA ─────────────────────────────────────
def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive data from logs."""
    if not data:
        return {}
    
    sensitive_keys = ['password', 'consumer_secret', 'api_key', 'token', 'pin', 'passkey']
    sanitized = {}
    
    for key, value in data.items():
        if key in sensitive_keys:
            sanitized[key] = '***'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_log_data(v) if isinstance(v, dict) else v for v in value]
        else:
            sanitized[key] = value
    
    return sanitized
