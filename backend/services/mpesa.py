# services/mpesa.py - M-Pesa Service (Production Ready)

import os
import base64
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from services.supabase_client import (
    get_supabase_client,
    create_payment,
    get_payment_by_checkout_id,
    update_payment,
    update_payment_status
)

logger = logging.getLogger(__name__)
load_dotenv()

# ─── CONFIG ────────────────────────────────────────────────
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', '')
MPESA_ENV = os.getenv('MPESA_ENV', 'production').lower()

# ─── BASE URL ──────────────────────────────────────────────
BASE_URL = (
    'https://sandbox.safaricom.co.ke'
    if MPESA_ENV == 'sandbox'
    else 'https://api.safaricom.co.ke'
)

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
_token_cache = {'token': None, 'expires_at': None}


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
    
    if MPESA_ENV == 'production' and len(MPESA_SHORTCODE) != 7:
        logger.error(f"❌ Production shortcode must be 7 digits: {MPESA_SHORTCODE}")
        return False
    
    if MPESA_ENV == 'production' and not CALLBACK_URL.startswith('https://'):
        logger.error("❌ Production callback must use HTTPS")
        return False
    
    logger.info(f"✅ M-Pesa configuration validated (Environment: {MPESA_ENV})")
    return True


# ─── PHONE NORMALIZER ──────────────────────────────────────
def normalize_phone(phone: str) -> str:
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


# ─── TOKEN ──────────────────────────────────────────────────
def get_mpesa_token(force: bool = False) -> str:
    """Get M-Pesa access token with caching."""
    global _token_cache

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
    reference: Optional[str] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Initiate STK Push to customer's phone and create payment record.
    """
    if not is_mpesa_configured():
        raise Exception("M-Pesa is not configured")

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
        "TransactionDesc": service[:36]
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
            res = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=REQUEST_TIMEOUT
            )
            
            if res.status_code != 200:
                logger.error(f"❌ STK Push failed (attempt {attempt+1}): {res.status_code}")
                logger.error(f"Response:
