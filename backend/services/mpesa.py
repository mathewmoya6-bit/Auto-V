# services/mpesa.py - PRODUCTION READY (With Auto-Confirmation & M-Pesa Verification)

import os
import base64
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# ─── IMPORT FROM supabase.py ──────────────────────────────
from services.supabase import get_supabase

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
    """Verify if IP belongs to Safaricom's production ranges."""
    if not ip:
        logger.warning("⚠️ No IP provided for verification")
        return False
    
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
        # Sandbox: accept localhost and any IP
        if ip in ['127.0.0.1', 'localhost']:
            return True
        return True


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

    # Remove non-digit characters
    phone = ''.join(c for c in phone if c.isdigit())

    # Remove leading 0
    if phone.startswith("0"):
        phone = "254" + phone[1:]

    # Add 254 if starting with 7
    if phone.startswith("7") and len(phone) == 9:
        phone = "254" + phone

    # Validate format
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
    reference: Optional[str] = None
) -> Dict[str, Any]:
    """Initiate STK Push to customer's phone."""
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
                logger.error(f"Response: {res.text[:500]}")
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
    """Query M-Pesa payment status."""
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


# ─── VERIFY TRANSACTION WITH M-PESA ───────────────────────
def verify_transaction_with_mpesa(checkout_request_id: str) -> Dict[str, Any]:
    """
    Verify transaction directly with M-Pesa API.
    This actually checks if the payment was successful.
    """
    try:
        # Get fresh token
        token = get_mpesa_token(force=True)
        
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
        
        response = requests.post(
            f"{BASE_URL}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code != 200:
            return {"verified": False, "error": f"API error: {response.status_code}"}
        
        data = response.json()
        logger.info(f"📥 Verification response: {data}")
        
        # Check M-Pesa's verification
        result_code = data.get("ResultCode")
        result_desc = data.get("ResultDesc")
        
        if result_code == "0":
            # Payment was successful - extract receipt
            metadata = data.get("CallbackMetadata", {})
            items = metadata.get("Item", [])
            
            receipt = None
            amount = None
            phone = None
            
            for item in items:
                name = item.get("Name")
                value = item.get("Value")
                
                if name == "MpesaReceiptNumber":
                    receipt = value
                elif name == "Amount":
                    amount = value
                elif name == "PhoneNumber":
                    phone = value
            
            return {
                "verified": True,
                "status": "completed",
                "receipt": receipt,
                "amount": amount,
                "phone": phone,
                "result_code": result_code,
                "result_desc": result_desc
            }
        else:
            return {
                "verified": False,
                "status": "failed",
                "result_code": result_code,
                "result_desc": result_desc
            }
            
    except Exception as e:
        logger.error(f"Transaction verification error: {e}")
        return {"verified": False, "error": str(e)}


# ─── CALLBACK HANDLER ──────────────────────────────────────
def handle_mpesa_callback(callback_data: Dict[str, Any], client_ip: str = None) -> Dict[str, Any]:
    """Handle M-Pesa callback with proper transaction extraction."""
    try:
        logger.info("=" * 60)
        logger.info("📥 Processing M-Pesa callback")
        
        if not callback_data:
            logger.error("❌ No callback data")
            return {"ResultCode": 1, "ResultDesc": "No data"}

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

        # ─── Use Supabase ──────────────────────────────────────────
        supabase = get_supabase()

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

        if payment.get("status") == "completed":
            logger.info(f"ℹ️ Payment {payment_id} already completed")
            return {"ResultCode": 0, "ResultDesc": "Already processed"}

        if result_code == "0" and transaction_id:
            update = {
                "status": "completed",
                "transaction_id": transaction_id,
                "mpesa_receipt_number": transaction_id,
                "amount_paid": amount,
                "completed_at": datetime.now().isoformat(),
                "mpesa_result_code": result_code,
                "mpesa_result_desc": result_desc or "Transaction completed",
                "verified_by": "mpesa_callback"
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


# ─── AUTO-CONFIRM PAYMENT ──────────────────────────────────
def auto_confirm_payment(payment_id: str) -> Dict[str, Any]:
    """
    Automatically confirm a payment by verifying with M-Pesa API.
    This replaces the manual "I've Confirmed" button.
    """
    try:
        logger.info(f"🔍 Auto-confirming payment: {payment_id}")
        
        # Get Supabase client
        supabase = get_supabase()
        
        # Get payment from database
        payment = supabase.table("payments") \
            .select("*") \
            .eq("id", payment_id) \
            .execute()
        
        if not payment.data:
            return {"success": False, "error": "Payment not found"}
        
        payment = payment.data[0]
        checkout_id = payment.get("checkout_request_id")
        
        if not checkout_id:
            return {"success": False, "error": "No checkout ID found"}
        
        # Check if already completed
        if payment.get("status") == "completed":
            return {
                "success": True, 
                "message": "Payment already completed",
                "payment": payment,
                "mpesa_verified": True
            }
        
        # ─── VERIFY WITH M-PESA ──────────────────────────────────────────
        verification = verify_transaction_with_mpesa(checkout_id)
        
        if verification.get("verified"):
            # M-Pesa confirmed the payment
            update_data = {
                "status": "completed",
                "transaction_id": verification.get("receipt"),
                "mpesa_receipt_number": verification.get("receipt"),
                "amount_paid": verification.get("amount"),
                "completed_at": datetime.now().isoformat(),
                "verified_by": "mpesa_api_auto",
                "verification_timestamp": datetime.now().isoformat(),
                "mpesa_result_code": verification.get("result_code"),
                "mpesa_result_desc": verification.get("result_desc")
            }
            
            result = supabase.table("payments") \
                .update(update_data) \
                .eq("id", payment_id) \
                .execute()
            
            if result.data:
                logger.info(f"✅ Payment {payment_id} auto-confirmed via M-Pesa API")
                return {
                    "success": True,
                    "message": "Payment verified by M-Pesa",
                    "payment": result.data[0],
                    "mpesa_verified": True,
                    "receipt": verification.get("receipt")
                }
            else:
                return {"success": False, "error": "Database update failed"}
        else:
            # M-Pesa says payment failed or not found
            return {
                "success": False,
                "error": "M-Pesa verification failed",
                "details": verification.get("result_desc", "Payment not found in M-Pesa system"),
                "result_code": verification.get("result_code"),
                "mpesa_verified": False
            }
            
    except Exception as e:
        logger.error(f"Auto-confirm error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─── GET PAYMENT STATUS ────────────────────────────────────
def get_payment_status(payment_id: str) -> Dict[str, Any]:
    """
    Get payment status from database and optionally verify with M-Pesa.
    """
    try:
        supabase = get_supabase()
        
        payment = supabase.table("payments") \
            .select("*") \
            .eq("id", payment_id) \
            .execute()
        
        if not payment.data:
            return {"status": "not_found", "error": "Payment not found"}
        
        payment = payment.data[0]
        
        # If payment is pending, try to auto-verify
        if payment.get("status") in ["pending", "processing"]:
            # Check if enough time has passed (30 seconds)
            created_at = payment.get("created_at")
            if created_at:
                try:
                    created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    elapsed = (datetime.now() - created_time).total_seconds()
                    
                    # Only auto-verify after 30 seconds
                    if elapsed > 30:
                        logger.info(f"⏳ Payment {payment_id} pending for {elapsed}s, auto-verifying...")
                        auto_result = auto_confirm_payment(payment_id)
                        if auto_result.get("success"):
                            return {
                                "status": "completed",
                                "payment": auto_result.get("payment"),
                                "mpesa_verified": True,
                                "receipt": auto_result.get("receipt")
                            }
                except Exception as e:
                    logger.warning(f"Error checking payment age: {e}")
        
        return {
            "status": payment.get("status", "unknown"),
            "payment": payment,
            "mpesa_verified": payment.get("verified_by") in ["mpesa_api_auto", "mpesa_callback"]
        }
        
    except Exception as e:
        logger.error(f"Get payment status error: {e}")
        return {"status": "error", "error": str(e)}


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


# ─── TEST FUNCTION ──────────────────────────────────────────
if __name__ == "__main__":
    print("🔍 Testing M-Pesa Configuration...")
    print(f"   Environment: {MPESA_ENV}")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Shortcode: {MPESA_SHORTCODE}")
    print(f"   Callback URL: {CALLBACK_URL}")
    
    # Check configuration
    if is_mpesa_configured():
        print("✅ M-Pesa is configured")
        
        # Test token
        try:
            token = get_mpesa_token(force=True)
            print(f"✅ Token obtained: {token[:20]}...")
        except Exception as e:
            print(f"❌ Token error: {e}")
    else:
        print("❌ M-Pesa is NOT configured")
        print("   Please set all required environment variables:")
        print("   - MPESA_CONSUMER_KEY")
        print("   - MPESA_CONSUMER_SECRET")
        print("   - MPESA_PASSKEY")
        print("   - MPESA_SHORTCODE")
        print("   - MPESA_CALLBACK_URL")
