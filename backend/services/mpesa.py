# services/mpesa.py - M-Pesa Service (Minimal Working Version)

import os
import base64
import logging
import requests
import time
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
    Initiate STK Push to customer's phone.
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

            # ─── Create Payment Record ──────────────────────────────────
            try:
                from services.supabase_client import create_payment
                
                payment_data = {
                    'id': payment_id,
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
                "success": True,
                "payment_id": payment_id,
                "checkout_request_id": checkout_id,
                "merchant_request_id": data.get("MerchantRequestID"),
                "response_code": data.get("ResponseCode"),
                "response_description": data.get("ResponseDescription")
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


# ─── CALLBACK HANDLER ──────────────────────────────────────
def handle_mpesa_callback(callback_data: Dict[str, Any], client_ip: str = None) -> Dict[str, Any]:
    """Handle M-Pesa callback and update payment status."""
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
        result_code = str(stk.get("ResultCode", "1"))
        result_desc = stk.get("ResultDesc", "Unknown error")

        logger.info(f"📊 CheckoutID: {checkout_id}, ResultCode: {result_code}")

        if not checkout_id:
            logger.error("❌ Missing CheckoutRequestID")
            return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}

        # ─── Extract transaction details ──────────────────────────────
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

        # ─── Get payment from database ──────────────────────────────────
        try:
            from services.supabase_client import get_payment_by_checkout_id, update_payment
            
            payment = get_payment_by_checkout_id(checkout_id)
            
            if not payment:
                logger.error(f"❌ Payment not found for CheckoutID: {checkout_id}")
                return {"ResultCode": 1, "ResultDesc": "Payment not found"}

            payment_id = payment.get("id")
            logger.info(f"✅ Found payment: {payment_id}")

            if payment.get("status") == "completed":
                logger.info(f"ℹ️ Payment {payment_id} already completed")
                return {"ResultCode": 0, "ResultDesc": "Already processed"}

            # ─── Update payment based on result ──────────────────────────────
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
                
                result = update_payment(payment_id, update_data)
                
                if result.get('success'):
                    logger.info(f"✅ Payment {payment_id} completed. Receipt: {transaction_id}")
                    return {"ResultCode": 0, "ResultDesc": "Success"}
                else:
                    logger.error(f"❌ Database update failed: {result.get('error')}")
                    return {"ResultCode": 1, "ResultDesc": "Update failed"}
                
            elif result_code in ["1037", "1032"]:
                update_data = {
                    "status": "cancelled",
                    "mpesa_result_code": result_code,
                    "mpesa_result_desc": result_desc or "Transaction cancelled"
                }
                update_payment(payment_id, update_data)
                logger.warning(f"⚠️ Payment {payment_id} cancelled")
                return {"ResultCode": 0, "ResultDesc": "Success"}
                
            else:
                update_data = {
                    "status": "failed",
                    "mpesa_result_code": result_code,
                    "mpesa_result_desc": result_desc or "Transaction failed"
                }
                update_payment(payment_id, update_data)
                logger.warning(f"❌ Payment {payment_id} failed: {result_desc}")
                return {"ResultCode": 0, "ResultDesc": "Success"}
                
        except ImportError as e:
            logger.error(f"❌ Database import error: {e}")
            return {"ResultCode": 1, "ResultDesc": "Database error"}

    except Exception as e:
        logger.error(f"❌ Callback error: {e}", exc_info=True)
        return {"ResultCode": 1, "ResultDesc": "System error"}


# ─── QUERY PAYMENT STATUS ──────────────────────────────────
def query_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    """Query M-Pesa payment status directly."""
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


# ─── VERIFY PAYMENT ──────────────────────────────────────────
def verify_payment_with_mpesa(checkout_request_id: str) -> Dict[str, Any]:
    """Verify payment with M-Pesa API and update database."""
    try:
        result = query_payment_status(checkout_request_id)
        
        result_code = result.get("ResultCode")
        result_desc = result.get("ResultDesc")
        
        if result_code == "0":
            metadata = result.get("CallbackMetadata", {})
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
            
            # Update payment in database
            try:
                from services.supabase_client import get_payment_by_checkout_id, update_payment
                
                payment = get_payment_by_checkout_id(checkout_request_id)
                if payment:
                    update_data = {
                        "status": "completed",
                        "mpesa_code": receipt,
                        "transaction_id": receipt,
                        "mpesa_result_code": result_code,
                        "mpesa_result_desc": result_desc,
                        "paid_at": datetime.now().isoformat()
                    }
                    if amount:
                        update_data["amount"] = amount
                    if phone:
                        update_data["mpesa_phone"] = phone
                    
                    update_payment(payment.get("id"), update_data)
            except Exception as db_err:
                logger.warning(f"Database update error: {db_err}")
            
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
                "status": "failed" if result_code != "1037" else "cancelled",
                "result_code": result_code,
                "result_desc": result_desc
            }
            
    except Exception as e:
        logger.error(f"Payment verification error: {e}")
        return {"verified": False, "error": str(e)}


# ─── AUTO-CONFIRM PAYMENT ──────────────────────────────────
def auto_confirm_payment(payment_id: str) -> Dict[str, Any]:
    """Auto-confirm a payment by verifying with M-Pesa API."""
    try:
        logger.info(f"🔍 Auto-confirming payment: {payment_id}")
        
        from services.supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        response = supabase.table('payments').select('*').eq('id', payment_id).execute()
        
        if not response.data:
            return {"success": False, "error": "Payment not found"}
        
        payment = response.data[0]
        checkout_id = payment.get('checkout_request_id')
        
        if not checkout_id:
            return {"success": False, "error": "No checkout ID found"}
        
        if payment.get('status') == 'completed':
            return {
                "success": True, 
                "message": "Payment already completed",
                "payment": payment,
                "mpesa_verified": True
            }
        
        verification = verify_payment_with_mpesa(checkout_id)
        
        if verification.get('verified'):
            return {
                "success": True,
                "message": "Payment verified by M-Pesa",
                "mpesa_verified": True,
                "receipt": verification.get('receipt')
            }
        else:
            return {
                "success": False,
                "error": "M-Pesa verification failed",
                "details": verification.get('result_desc'),
                "result_code": verification.get('result_code')
            }
            
    except Exception as e:
        logger.error(f"Auto-confirm error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─── FORCE COMPLETE PAYMENT ──────────────────────────────────
def force_complete_payment(payment_id: str, transaction_id: str) -> Dict[str, Any]:
    """Force complete a payment manually."""
    try:
        logger.info(f"📝 Force completing payment: {payment_id}")
        
        from services.supabase_client import get_supabase_client, update_payment
        
        supabase = get_supabase_client()
        response = supabase.table('payments').select('*').eq('id', payment_id).execute()
        
        if not response.data:
            return {"success": False, "error": "Payment not found"}
        
        payment = response.data[0]
        
        if payment.get('status') == 'completed':
            return {
                "success": True,
                "message": "Payment already completed",
                "payment": payment
            }
        
        update_data = {
            "status": "completed",
            "mpesa_code": transaction_id,
            "transaction_id": transaction_id,
            "mpesa_result_code": "0",
            "mpesa_result_desc": "Force completed manually",
            "paid_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = update_payment(payment_id, update_data)
        
        if result.get('success'):
            return {
                "success": True,
                "message": "Payment force completed",
                "payment": result.get('data')
            }
        else:
            return {"success": False, "error": result.get('error')}
            
    except Exception as e:
        logger.error(f"Force complete error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─── Exports ──────────────────────────────────────────────────

__all__ = [
    'initiate_stk_push',
    'handle_mpesa_callback',
    'query_payment_status',
    'verify_payment_with_mpesa',
    'auto_confirm_payment',
    'force_complete_payment',
    'is_mpesa_configured',
    'normalize_phone',
    'get_mpesa_token'
]
