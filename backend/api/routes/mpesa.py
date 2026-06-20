# services/mpesa.py – Complete Production File

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

# ─── CONFIG (Read from environment) ────────────────────────
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', '')
MPESA_ENV = os.getenv('MPESA_ENV', 'production').lower()

# ─── Production Validation ──────────────────────────────────
if MPESA_ENV == 'production':
    required = [MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET, MPESA_PASSKEY, CALLBACK_URL]
    if not all(required):
        missing = []
        if not MPESA_CONSUMER_KEY: missing.append('CONSUMER_KEY')
        if not MPESA_CONSUMER_SECRET: missing.append('CONSUMER_SECRET')
        if not MPESA_PASSKEY: missing.append('PASSKEY')
        if not CALLBACK_URL: missing.append('CALLBACK_URL')
        logger.critical(f"❌ Production: Missing M-Pesa credentials: {', '.join(missing)}")
        raise ValueError(f"Missing M-Pesa credentials: {', '.join(missing)}")

# ─── Base URL ───────────────────────────────────────────────
BASE_URL = (
    'https://sandbox.safaricom.co.ke'
    if MPESA_ENV == 'sandbox'
    else 'https://api.safaricom.co.ke'
)

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
_token_cache = {'token': None, 'expires_at': None}

# ─── Safaricom IPs (Production Security) ────────────────────
SAFARICOM_IPS = [
    '196.201.214.0/24',
    '196.201.215.0/24',
    '196.201.216.0/24',
    '196.201.217.0/24',
]

def verify_safaricom_ip(ip: str) -> bool:
    """Verify if IP belongs to Safaricom's ranges."""
    if MPESA_ENV != 'production':
        return True  # Skip validation in sandbox
    
    if not ip:
        return False
    
    try:
        import ipaddress
        ip_addr = ipaddress.ip_address(ip)
        for cidr in SAFARICOM_IPS:
            if ip_addr in ipaddress.ip_network(cidr):
                return True
        logger.warning(f"⚠️ Non-Safaricom IP attempted: {ip}")
        return False
    except Exception as e:
        logger.warning(f"IP verification error: {e}")
        return False


# ─── Phone Normalizer ──────────────────────────────────────
def normalize_phone(phone: str) -> str:
    """Format phone to 254XXXXXXXXX for M-Pesa."""
    if not phone:
        raise ValueError("Phone number required")
    
    phone = re.sub(r'[^\d]', '', phone)
    
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif phone.startswith('7') and len(phone) == 9:
        phone = '254' + phone
    
    if not phone.startswith('254') or len(phone) != 12:
        raise ValueError(f"Invalid phone format: {phone}")
    
    return phone


# ─── Safety Check ──────────────────────────────────────────
def is_mpesa_configured() -> bool:
    """Check if all M-Pesa credentials are present."""
    configured = all([
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_PASSKEY,
        MPESA_SHORTCODE,
        CALLBACK_URL
    ])
    if not configured:
        missing = []
        if not MPESA_CONSUMER_KEY: missing.append('CONSUMER_KEY')
        if not MPESA_CONSUMER_SECRET: missing.append('CONSUMER_SECRET')
        if not MPESA_PASSKEY: missing.append('PASSKEY')
        if not MPESA_SHORTCODE: missing.append('SHORTCODE')
        if not CALLBACK_URL: missing.append('CALLBACK_URL')
        logger.warning(f"⚠️ Missing M-Pesa: {', '.join(missing)}")
    return configured


# ─── Token ──────────────────────────────────────────────────
def get_mpesa_token(force: bool = False) -> str:
    """Get M-Pesa OAuth token with caching."""
    global _token_cache

    if (not force and _token_cache["token"] and _token_cache["expires_at"] and 
        datetime.now() < _token_cache["expires_at"]):
        return _token_cache["token"]

    auth = base64.b64encode(
        f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()
    ).decode()

    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(url, headers={"Authorization": f"Basic {auth}"}, timeout=REQUEST_TIMEOUT)
            res.raise_for_status()
            data = res.json()
            
            token = data.get("access_token")
            if not token:
                raise Exception("No access_token in response")
            
            _token_cache = {
                "token": token,
                "expires_at": datetime.now() + timedelta(seconds=3500)
            }
            
            logger.info(f"✅ M-Pesa token obtained ({MPESA_ENV})")
            return token
            
        except Exception as e:
            logger.warning(f"Token attempt {attempt+1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                raise Exception(f"Failed to get M-Pesa token: {str(e)}")


# ─── STK Push ──────────────────────────────────────────────
def initiate_stk_push(phone: str, amount: float, payment_id: str, service: str = "AUTO-V") -> Dict[str, Any]:
    """Send STK Push to customer phone."""
    if not is_mpesa_configured():
        raise Exception("M-Pesa not configured")
    
    token = get_mpesa_token()
    phone = normalize_phone(phone)
    
    amount_int = int(round(amount))
    if amount_int < 1:
        raise Exception("Amount must be at least 1 KES")
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()
    ).decode()
    
    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount_int,
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": f"AUTO-{payment_id[:6]}",
        "TransactionDesc": service[:50]
    }
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        data = res.json()
        
        response_code = data.get("ResponseCode")
        response_desc = data.get("ResponseDescription")
        checkout_id = data.get("CheckoutRequestID")
        
        if response_code != "0":
            raise Exception(f"STK Push failed: {response_desc} (Code: {response_code})")
        
        if not checkout_id:
            raise Exception("No CheckoutRequestID returned")
        
        return {
            "CheckoutRequestID": checkout_id,
            "MerchantRequestID": data.get("MerchantRequestID"),
            "ResponseCode": response_code,
            "ResponseDescription": response_desc
        }
        
    except Exception as e:
        logger.error(f"❌ STK Push failed: {e}")
        raise


# ─── Status Query ──────────────────────────────────────────
def query_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    """Query M-Pesa payment status."""
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
    
    try:
        res = requests.post(
            f"{BASE_URL}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logger.error(f"❌ Status query failed: {e}")
        raise


# ─── Callback Handler ──────────────────────────────────────
def handle_mpesa_callback(callback_data: Dict[str, Any], client_ip: str = None) -> Dict[str, Any]:
    """Process M-Pesa callback."""
    try:
        logger.info("📥 Processing M-Pesa callback")
        
        # IP Verification
        if client_ip and not verify_safaricom_ip(client_ip):
            logger.warning(f"⚠️ Non-Safaricom IP: {client_ip}")
            return {"ResultCode": 1, "ResultDesc": "Invalid IP"}
        
        if not callback_data:
            return {"ResultCode": 1, "ResultDesc": "No data"}
        
        stk = callback_data.get("Body", {}).get("stkCallback", {})
        if not stk:
            return {"ResultCode": 1, "ResultDesc": "Missing stkCallback"}
        
        checkout_id = stk.get("CheckoutRequestID")
        result_code = str(stk.get("ResultCode"))
        result_desc = stk.get("ResultDesc")
        
        if not checkout_id:
            return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}
        
        # Extract transaction details
        transaction_id = None
        amount = None
        
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
        
        # Update database
        supabase = get_supabase()
        payment = supabase.table("payments").select("*").eq("checkout_request_id", checkout_id).execute()
        
        if not payment.data:
            return {"ResultCode": 1, "ResultDesc": "Payment not found"}
        
        payment = payment.data[0]
        payment_id = payment["id"]
        
        if payment["status"] == "completed":
            return {"ResultCode": 0, "ResultDesc": "Already processed"}
        
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
                "status": "failed",
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction cancelled"
            }
            logger.warning(f"⚠️ Payment {payment_id} cancelled")
        else:
            update = {
                "status": "failed",
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or f"Transaction failed"
            }
            logger.warning(f"❌ Payment {payment_id} failed: {result_desc}")
        
        result = supabase.table("payments").update(update).eq("id", payment_id).execute()
        
        if result.data:
            logger.info(f"✅ Database updated: {result.data[0].get('status')}")
            return {"ResultCode": 0, "ResultDesc": "Success"}
        else:
            return {"ResultCode": 1, "ResultDesc": "Update failed"}
    
    except Exception as e:
        logger.error(f"❌ Callback error: {e}", exc_info=True)
        return {"ResultCode": 1, "ResultDesc": str(e)}


# ─── Sanitize Log Data ─────────────────────────────────────
def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive data from logs."""
    if not data:
        return {}
    
    sensitive_keys = ['password', 'consumer_secret', 'api_key', 'token', 'pin']
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
