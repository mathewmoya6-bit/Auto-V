# services/mpesa.py – FIXED: Remove non-existent column

import os
import base64
import logging
import requests
import time
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from functools import wraps
from dotenv import load_dotenv
from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
load_dotenv()

# ─── PRODUCTION CONFIGURATION ────────────────────────────────
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', 'LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', 'aGGo8AuPJVpsZLcs')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
MPESA_SHORTCODE_TYPE = os.getenv('MPESA_SHORTCODE_TYPE', 'paybill')
CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', '')
MPESA_ENV = os.getenv('MPESA_ENV', 'production').lower()

BASE_URL = 'https://api.safaricom.co.ke'  # Production endpoint

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2

_token_cache = {
    'token': None,
    'expires_at': None,
    'acquired_at': None
}


# ─── VALIDATION ──────────────────────────────────────────────
def is_mpesa_configured() -> bool:
    """Check if M-Pesa is properly configured."""
    required = [
        MPESA_CONSUMER_KEY,
        MPESA_CONSUMER_SECRET,
        MPESA_PASSKEY,
        CALLBACK_URL
    ]
    
    if not all(required):
        missing = [k for k, v in zip(['Consumer Key', 'Consumer Secret', 'Passkey', 'Callback URL'], required) if not v]
        logger.error(f"❌ Missing configuration: {', '.join(missing)}")
        return False
    
    if len(MPESA_SHORTCODE) != 7:
        logger.error(f"❌ Invalid shortcode: {MPESA_SHORTCODE}")
        return False
    
    if not CALLBACK_URL.startswith('https://'):
        logger.error("❌ Callback URL must use HTTPS in production")
        return False
    
    logger.info("✅ M-Pesa production configuration validated")
    return True


def verify_safaricom_ip(ip: str) -> bool:
    """Verify if an IP address belongs to Safaricom's production ranges."""
    if not ip:
        logger.warning("⚠️ No IP address provided for verification")
        return False
    
    SAFARICOM_IP_RANGES = [
        '196.201.214.0/24',
        '196.201.215.0/24', 
        '196.201.216.0/24',
        '196.201.217.0/24',
        '196.201.218.0/24',
        '196.201.219.0/24',
        '196.201.220.0/24',
        '196.201.221.0/24',
    ]
    
    try:
        import ipaddress
        ip_addr = ipaddress.ip_address(ip)
        for cidr in SAFARICOM_IP_RANGES:
            if ip_addr in ipaddress.ip_network(cidr):
                logger.info(f"✅ IP {ip} verified as Safaricom production range")
                return True
        
        # In production, ONLY allow Safaricom IPs
        logger.warning(f"❌ IP {ip} not in Safaricom production ranges")
        return False
        
    except Exception as e:
        logger.error(f"❌ IP verification error: {e}")
        return False


def normalize_phone(phone: str) -> str:
    """Normalize phone number to 254XXXXXXXXX format."""
    if not phone:
        raise ValueError("Phone number is required")
    
    phone = ''.join(filter(str.isdigit, phone))
    
    if phone.startswith('0'):
        phone = phone[1:]
    
    if not phone.startswith('254'):
        if phone.startswith('7') and len(phone) == 9:
            phone = '254' + phone
        elif len(phone) == 10 and phone.startswith('7'):
            phone = '254' + phone[1:]
    
    if not phone.startswith('254') or len(phone) != 12:
        raise ValueError(f"Invalid phone number format: {phone}")
    
    return phone


# ─── TOKEN MANAGEMENT ────────────────────────────────────────
def get_mpesa_token(force: bool = False) -> str:
    """Get M-Pesa access token with caching."""
    global _token_cache
    
    if not force and _token_cache['token'] and _token_cache['expires_at']:
        if datetime.now() < _token_cache['expires_at']:
            logger.debug("✅ Using cached M-Pesa token")
            return _token_cache['token']
    
    logger.info("🔄 Acquiring new M-Pesa access token")
    
    auth_string = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/json'
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Token request failed (attempt {attempt + 1}): {response.status_code}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                raise Exception(f"Token request failed: {response.status_code}")
            
            data = response.json()
            
            if 'access_token' not in data:
                logger.error(f"❌ No access_token in response: {data}")
                raise Exception("Invalid token response from M-Pesa")
            
            token = data['access_token']
            
            _token_cache = {
                'token': token,
                'expires_at': datetime.now() + timedelta(seconds=3540),
                'acquired_at': datetime.now()
            }
            
            logger.info("✅ M-Pesa token acquired successfully")
            return token
            
        except Exception as e:
            logger.error(f"❌ Token request error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            raise


# ─── STK PUSH ──────────────────────────────────────────────────
def initiate_stk_push(
    phone: str,
    amount: float,
    payment_id: str,
    service: str = "AUTO-V",
    account_reference: Optional[str] = None
) -> Dict[str, Any]:
    """Initiate STK Push payment in production."""
    if not is_mpesa_configured():
        raise Exception("M-Pesa is not properly configured")
    
    if amount <= 0:
        raise ValueError("Amount must be greater than 0")
    
    if amount < 1:
        raise ValueError("Minimum payment is 1 KES")
    
    phone = normalize_phone(phone)
    token = get_mpesa_token()
    
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
        "CallBackURL": CALLBACK_URL,
        "AccountReference": account_reference or f"AUTO-{payment_id[:8].upper()}",
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
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.error(f"❌ STK Push failed (attempt {attempt + 1}): {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                raise Exception(f"STK Push failed: {response.status_code}")
            
            data = response.json()
            logger.info(f"📥 STK Push response: {data}")
            
            if data.get("ResponseCode") != "0":
                error_msg = data.get("ResponseDescription", "Unknown error")
                raise Exception(f"M-Pesa error: {error_msg}")
            
            checkout_id = data.get("CheckoutRequestID")
            if not checkout_id:
                raise Exception("No CheckoutRequestID returned from M-Pesa")
            
            # ─── FIXED: Update payment with checkout ID ──────────────
            # Only update columns that exist in the database
            supabase = get_supabase()
            result = supabase.table('payments').update({
                'checkout_request_id': checkout_id,
                'merchant_request_id': data.get("MerchantRequestID"),
                'updated_at': datetime.now().isoformat()
            }).eq('id', payment_id).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ Database update error: {result.error}")
            
            logger.info(f"✅ STK Push initiated: {checkout_id}")
            
            return {
                "CheckoutRequestID": checkout_id,
                "MerchantRequestID": data.get("MerchantRequestID"),
                "ResponseCode": data.get("ResponseCode"),
                "ResponseDescription": data.get("ResponseDescription"),
                "CustomerMessage": data.get("CustomerMessage", "STK Push sent to your phone")
            }
            
        except Exception as e:
            logger.error(f"❌ STK Push error (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            raise


# ─── STATUS QUERY ────────────────────────────────────────────
def query_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    """Query payment status from M-Pesa."""
    if not checkout_request_id:
        raise ValueError("CheckoutRequestID is required")
    
    token = get_mpesa_token()
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_str = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()
    
    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id
    }
    
    logger.info(f"🔍 Querying payment status: {checkout_request_id}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{BASE_URL}/mpesa/stkpushquery/v1/query"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Status query failed (attempt {attempt + 1}): {response.status_code}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                raise Exception(f"Status query failed: {response.status_code}")
            
            data = response.json()
            logger.info(f"📥 Status query response: {data}")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Status query error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            raise


# ─── CALLBACK HANDLER ────────────────────────────────────────
def handle_mpesa_callback(callback_data: Dict[str, Any], client_ip: str = None) -> Dict[str, Any]:
    """Handle M-Pesa callback with proper validation."""
    try:
        logger.info("=" * 60)
        logger.info("📥 Processing M-Pesa callback")
        
        if client_ip:
            if not verify_safaricom_ip(client_ip):
                logger.error(f"❌ Callback from unauthorized IP: {client_ip}")
                return {"ResultCode": 1, "ResultDesc": "Unauthorized IP"}
        
        if not callback_data:
            logger.error("❌ No callback data received")
            return {"ResultCode": 1, "ResultDesc": "No data"}
        
        stk = callback_data.get("Body", {}).get("stkCallback", {})
        
        if not stk:
            logger.error("❌ Invalid callback structure - missing stkCallback")
            return {"ResultCode": 1, "ResultDesc": "Invalid callback structure"}
        
        checkout_id = stk.get("CheckoutRequestID")
        result_code = str(stk.get("ResultCode", "1"))
        result_desc = stk.get("ResultDesc", "Unknown")
        
        logger.info(f"📊 Callback: CheckoutID={checkout_id}, ResultCode={result_code}")
        
        if not checkout_id:
            logger.error("❌ Missing CheckoutRequestID in callback")
            return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}
        
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
        
        supabase = get_supabase()
        
        payment_result = supabase.table('payments') \
            .select("*") \
            .eq("checkout_request_id", checkout_id) \
            .execute()
        
        if not payment_result.data:
            logger.error(f"❌ Payment not found for CheckoutID: {checkout_id}")
            return {"ResultCode": 1, "ResultDesc": "Payment not found"}
        
        payment = payment_result.data[0]
        payment_id = payment["id"]
        
        if payment.get("status") in ["completed", "failed"]:
            logger.info(f"ℹ️ Payment {payment_id} already processed: {payment.get('status')}")
            return {"ResultCode": 0, "ResultDesc": "Already processed"}
        
        # ─── FIXED: Only update columns that exist ──────────────
        if result_code == "0" and transaction_id:
            update_data = {
                "status": "completed",
                "transaction_id": transaction_id,
                "mpesa_receipt_number": transaction_id,
                "amount_paid": amount,
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc,
                "completed_at": datetime.now().isoformat()
            }
            logger.info(f"✅ Payment {payment_id} completed! Receipt: {transaction_id}")
            
        elif result_code in ["1037", "1032"]:
            update_data = {
                "status": "failed",
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction cancelled by user"
            }
            logger.warning(f"⚠️ Payment {payment_id} cancelled by user")
            
        elif result_code == "2001":
            update_data = {
                "status": "pending",
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction still processing"
            }
            logger.warning(f"⏳ Payment {payment_id} still pending (timeout)")
            
        else:
            update_data = {
                "status": "failed",
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction failed"
            }
            logger.error(f"❌ Payment {payment_id} failed: {result_desc}")
        
        result = supabase.table('payments').update(update_data).eq("id", payment_id).execute()
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"❌ Database update error: {result.error}")
            return {"ResultCode": 1, "ResultDesc": "Database update failed"}
        
        logger.info(f"✅ Callback processed successfully for payment {payment_id}")
        return {"ResultCode": 0, "ResultDesc": "Success"}
        
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
