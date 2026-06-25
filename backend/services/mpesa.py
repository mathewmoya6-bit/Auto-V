# ============================================================
# services/mpesa.py - M-Pesa Service Logic (REAL API)
# ============================================================

import os
import base64
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Import Supabase client
from services.supabase_client import (
    create_payment,
    get_payment_by_checkout_request_id,
    get_payment_by_payment_id,
    update_payment_status,
    get_payment_status
)

load_dotenv()

logger = logging.getLogger(__name__)

# ─── M-Pesa Configuration ──────────────────────────────────
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "4095377")
MPESA_ENV = os.getenv("MPESA_ENV", "sandbox").lower().strip()

# ─── Callback URL ──────────────────────────────────────────
# IMPORTANT: Use your Render URL here
MPESA_CALLBACK_URL = os.getenv(
    "MPESA_CALLBACK_URL",
    "https://auto-v.onrender.com/api/mpesa/callback"
)

# ─── Base URLs ─────────────────────────────────────────────
BASE_URLS = {
    "production": "https://api.safaricom.co.ke",
    "sandbox": "https://sandbox.safaricom.co.ke"
}
BASE_URL = BASE_URLS.get(MPESA_ENV, BASE_URLS["sandbox"])

logger.info(f"🔧 M-Pesa Environment: {MPESA_ENV}")
logger.info(f"🔧 M-Pesa Base URL: {BASE_URL}")
logger.info(f"🔧 M-Pesa Shortcode: {MPESA_SHORTCODE}")
logger.info(f"🔧 M-Pesa Callback URL: {MPESA_CALLBACK_URL}")


def get_mpesa_token() -> Optional[str]:
    """Get M-Pesa OAuth token from Safaricom."""
    try:
        if not MPESA_CONSUMER_KEY or not MPESA_CONSUMER_SECRET:
            logger.error("❌ M-Pesa credentials not configured")
            return None

        # Encode credentials
        credentials = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        # Make request
        url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
        headers = {"Authorization": f"Basic {encoded_credentials}"}

        logger.info(f"🔄 Fetching M-Pesa token from {url}")

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            token = response.json().get("access_token")
            logger.info("✅ M-Pesa token obtained successfully")
            return token
        else:
            logger.error(f"❌ Failed to get M-Pesa token: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None

    except Exception as e:
        logger.error(f"❌ M-Pesa token error: {e}")
        return None


def initiate_stk_push(
    phone: str,
    amount: float,
    payment_id: str,
    reference: str = None,
    user_id: str = None
) -> Dict[str, Any]:
    """
    Initiate M-Pesa STK Push payment using Safaricom API.
    """
    try:
        # Get token
        token = get_mpesa_token()
        if not token:
            raise ValueError("❌ Failed to get M-Pesa token. Check your credentials.")

        # Format phone number (ensure it starts with 254)
        original_phone = phone
        if phone.startswith("0"):
            phone = "254" + phone[1:]
        elif phone.startswith("+"):
            phone = phone[1:]
        elif not phone.startswith("254"):
            phone = "254" + phone

        logger.info(f"📱 Phone formatted: {original_phone} → {phone}")

        # Generate timestamp and password
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()

        # Build payload
        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(round(amount)),
            "PartyA": phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": MPESA_CALLBACK_URL,  # Use the variable
            "AccountReference": reference or f"AUTO-{payment_id[-8:]}",
            "TransactionDesc": f"Payment {payment_id}"
        }

        if user_id:
            payload["TransactionDesc"] = f"{payload['TransactionDesc']} - User {user_id}"

        # Log request (hide sensitive data)
        log_payload = payload.copy()
        log_payload["Password"] = "***HIDDEN***"
        logger.info(f"📤 STK Push Request: {log_payload}")

        # Make request to Safaricom
        url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)

        # Log response
        logger.info(f"📥 STK Push Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ STK Push Response: {result}")

            # Check if the request was successful
            if result.get("ResponseCode") == "0":
                checkout_request_id = result.get("CheckoutRequestID")
                merchant_request_id = result.get("MerchantRequestID")
                
                logger.info(f"✅ STK Push initiated successfully for {phone}")
                logger.info(f"   CheckoutRequestID: {checkout_request_id}")
                logger.info(f"   MerchantRequestID: {merchant_request_id}")
                
                # ─── SAVE TO DATABASE ──────────────────────────────────
                # Create payment record in Supabase
                try:
                    payment_data = {
                        "payment_id": payment_id,
                        "user_id": user_id,
                        "phone": phone,
                        "amount": float(amount),
                        "status": "pending",
                        "reference": reference or f"AUTO-{payment_id[-8:]}",
                        "checkout_request_id": checkout_request_id,
                        "merchant_request_id": merchant_request_id,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    create_payment(payment_data)
                    logger.info(f"💾 Payment record created in database: {payment_id}")
                    
                except Exception as db_error:
                    logger.error(f"❌ Failed to save payment to database: {db_error}")
                    # Continue - we still want to return the STK response
                
                return result
            else:
                error_msg = result.get("ResponseDescription", "Unknown error")
                logger.error(f"❌ STK Push failed: {error_msg}")
                raise ValueError(f"STK Push failed: {error_msg}")
        else:
            logger.error(f"❌ STK Push HTTP Error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise ValueError(f"STK Push failed: HTTP {response.status_code}")

    except requests.exceptions.Timeout:
        logger.error("❌ STK Push timeout - Safaricom API not responding")
        raise ValueError("STK Push timeout - please try again")
    except requests.exceptions.ConnectionError:
        logger.error("❌ STK Push connection error - cannot reach Safaricom")
        raise ValueError("Connection error - check your internet")
    except Exception as e:
        logger.error(f"❌ STK Push error: {e}")
        raise


def handle_mpesa_callback(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle M-Pesa callback from Safaricom."""
    try:
        body = data.get("Body", {})
        stk_callback = body.get("stkCallback", {})

        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        merchant_request_id = stk_callback.get("MerchantRequestID")

        # Extract metadata
        metadata = stk_callback.get("CallbackMetadata", {})
        items = metadata.get("Item", [])

        meta_dict = {}
        for item in items:
            name = item.get("Name")
            value = item.get("Value")
            if name:
                meta_dict[name] = value

        # Determine status
        if result_code == 0:
            status = "completed"
        elif result_code == 1037:
            status = "cancelled"  # User cancelled the transaction
        elif result_code == 1032:
            status = "failed"  # Transaction failed
        else:
            status = "failed"

        logger.info(
            f"📩 Callback: {checkout_request_id} → {status}",
            extra={
                "result_code": result_code,
                "result_desc": result_desc,
                "mpesa_code": meta_dict.get("MpesaReceiptNumber"),
                "amount": meta_dict.get("Amount")
            }
        )

        # ─── UPDATE DATABASE ──────────────────────────────────────────
        if checkout_request_id:
            try:
                # Find the payment by checkout_request_id
                payment = get_payment_by_checkout_request_id(checkout_request_id)
                
                if payment:
                    logger.info(f"💾 Found payment: {payment.get('payment_id')}")
                    
                    # Update payment status and details
                    update_data = {
                        "status": status,
                        "result_code": result_code,
                        "result_desc": result_desc,
                        "mpesa_receipt": meta_dict.get("MpesaReceiptNumber"),
                        "transaction_date": meta_dict.get("TransactionDate"),
                        "amount": meta_dict.get("Amount"),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    # If completed, also store the receipt number
                    if status == "completed":
                        update_data["mpesa_receipt"] = meta_dict.get("MpesaReceiptNumber")
                        update_data["transaction_date"] = meta_dict.get("TransactionDate")
                        logger.info(f"✅ Payment completed! Receipt: {meta_dict.get('MpesaReceiptNumber')}")
                    
                    update_payment_status(payment["payment_id"], update_data)
                    logger.info(f"💾 Payment updated in database: {payment['payment_id']} → {status}")
                    
                else:
                    logger.warning(f"⚠️ Payment not found for checkout_request_id: {checkout_request_id}")
                    # Try to find by merchant_request_id as fallback
                    if merchant_request_id:
                        payment = get_payment_by_checkout_request_id(merchant_request_id)
                        if payment:
                            logger.info(f"💾 Found payment by merchant_request_id: {payment.get('payment_id')}")
                            update_payment_status(payment["payment_id"], {
                                "status": status,
                                "result_code": result_code,
                                "result_desc": result_desc,
                                "mpesa_receipt": meta_dict.get("MpesaReceiptNumber"),
                                "transaction_date": meta_dict.get("TransactionDate"),
                                "amount": meta_dict.get("Amount"),
                                "updated_at": datetime.utcnow().isoformat()
                            })
                    
            except Exception as db_error:
                logger.error(f"❌ Failed to update payment in database: {db_error}")
                # Continue - we still want to return success to Safaricom
        else:
            logger.warning("⚠️ No checkout_request_id in callback")

        return {
            "ResultCode": 0,
            "ResultDesc": "Success",
            "data": {
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
                "status": status,
                "result_code": result_code,
                "result_desc": result_desc,
                "mpesa_code": meta_dict.get("MpesaReceiptNumber"),
                "amount": meta_dict.get("Amount"),
                "transaction_date": meta_dict.get("TransactionDate")
            }
        }

    except Exception as e:
        logger.error(f"❌ Callback handling error: {e}")
        import traceback
        traceback.print_exc()
        return {"ResultCode": 1, "ResultDesc": f"Error: {str(e)}"}


def query_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    """Query payment status from Safaricom."""
    try:
        token = get_mpesa_token()
        if not token:
            raise ValueError("Failed to get M-Pesa token")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()

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

        if response.status_code == 200:
            result = response.json()
            
            # Also update database with the query result
            try:
                payment = get_payment_by_checkout_request_id(checkout_request_id)
                if payment:
                    result_code = result.get("ResultCode")
                    if result_code == 0:
                        update_payment_status(payment["payment_id"], {
                            "status": "completed",
                            "updated_at": datetime.utcnow().isoformat()
                        })
                    elif result_code in [1037, 1032]:
                        update_payment_status(payment["payment_id"], {
                            "status": "failed",
                            "updated_at": datetime.utcnow().isoformat()
                        })
            except Exception as db_error:
                logger.error(f"❌ Failed to update payment from query: {db_error}")
            
            return result
        else:
            logger.error(f"Query failed: {response.status_code}")
            raise ValueError(f"Query failed: {response.text}")

    except Exception as e:
        logger.error(f"Query error: {e}")
        raise


def auto_confirm_payment(payment_id: str) -> Dict[str, Any]:
    """Auto-confirm a pending payment (admin override)."""
    try:
        # Check if payment exists
        payment = get_payment_by_payment_id(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        # Update status to completed
        update_data = {
            "status": "completed",
            "result_code": 0,
            "result_desc": "Auto-confirmed by admin",
            "updated_at": datetime.utcnow().isoformat()
        }
        
        update_payment_status(payment_id, update_data)
        
        return {
            "success": True,
            "message": "Payment auto-confirmed",
            "payment_id": payment_id,
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Auto-confirm error: {e}")
        raise


def is_mpesa_configured() -> bool:
    """Check if M-Pesa is properly configured."""
    configured = bool(
        MPESA_CONSUMER_KEY and
        MPESA_CONSUMER_SECRET and
        MPESA_PASSKEY
    )
    if not configured:
        logger.warning("⚠️ M-Pesa not fully configured - missing credentials")
    return configured


def get_mpesa_token_public() -> Optional[Dict[str, Any]]:
    """Public wrapper for get_mpesa_token."""
    token = get_mpesa_token()
    if token:
        return {"token": token, "expires_in": 3600}
    return None


def get_payment_status_by_id(payment_id: str) -> Dict[str, Any]:
    """Get payment status from database by payment_id."""
    try:
        payment = get_payment_by_payment_id(payment_id)
        if payment:
            return {
                "payment_id": payment.get("payment_id"),
                "status": payment.get("status", "pending"),
                "amount": payment.get("amount"),
                "phone": payment.get("phone"),
                "mpesa_receipt": payment.get("mpesa_receipt"),
                "created_at": payment.get("created_at"),
                "updated_at": payment.get("updated_at")
            }
        else:
            return {"payment_id": payment_id, "status": "not_found"}
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        return {"payment_id": payment_id, "status": "error", "error": str(e)}
