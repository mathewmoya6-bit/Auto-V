# app.py
# AUTO-V M-Pesa Backend - Flask version
# Entry point fixed: env loading, CORS, port handling

import os
import base64
import json
import datetime
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import httpx
from supabase import create_client, Client

# ============================================================
# LOAD ENVIRONMENT VARIABLES (FIXED ENTRY)
# ============================================================
load_dotenv()  # ← This is critical

# ============================================================
# LOGGING SETUP
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================
app = Flask(__name__)

# ✅ CORS - Allow frontend domain (change in production)
CORS(app, origins=["*"])  # For development

# Supabase - SINGLE SOURCE OF TRUTH
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tsvejnzxrxrrecgquxbq.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTE4NzM2OCwiZXhwIjoyMDk2NzYzMzY4fQ.LdF2qU2J4PZ_XGmNUnK7Bs33C3P1_SFyo1Jh6sQ2Fjo"
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# M-Pesa Credentials
MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv")
MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "aGGo8AuPJVpsZLcs")
MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY", "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277")
MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "4095377")
MPESA_ENVIRONMENT = os.environ.get("MPESA_ENVIRONMENT", "sandbox")

# Base URL for M-Pesa API
MPESA_API_BASE = "https://api.safaricom.co.ke" if MPESA_ENVIRONMENT == "production" else "https://sandbox.safaricom.co.ke"

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def generate_timestamp() -> str:
    """Generate timestamp in M-Pesa format (YYYYMMDDHHmmss)"""
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

def generate_password(timestamp: str) -> str:
    """Generate M-Pesa password (Base64 encoded)"""
    data = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
    return base64.b64encode(data.encode()).decode()

def format_phone(phone: str) -> str:
    """Validate and format phone number to international format"""
    cleaned = ''.join(c for c in phone if c.isdigit())
    if cleaned.startswith('0'):
        cleaned = '254' + cleaned[1:]
    elif cleaned.startswith('7') and len(cleaned) == 9:
        cleaned = '254' + cleaned
    elif len(cleaned) == 10 and cleaned.startswith('07'):
        cleaned = '254' + cleaned[1:]
    return cleaned

def get_mpesa_access_token() -> str:
    """Get M-Pesa OAuth Access Token"""
    auth_str = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
    auth_bytes = auth_str.encode()
    auth_b64 = base64.b64encode(auth_bytes).decode()
    
    with httpx.Client() as client:
        response = client.get(
            f"{MPESA_API_BASE}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth_b64}"}
        )
        if response.status_code != 200:
            logger.error(f"Failed to get M-Pesa access token: {response.text}")
            raise Exception("M-Pesa authentication failed")
        
        data = response.json()
        return data["access_token"]

# ============================================================
# ROUTES (ALREADY CORRECT - NO CHANGES NEEDED)
# ============================================================

@app.route('/', methods=['GET'])
def root():
    return jsonify({"message": "AUTO-V M-Pesa Backend is running"})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat()
    })

@app.route('/api/mpesa/initiate', methods=['POST'])
def initiate_payment():
    """
    Initiate M-Pesa STK Push
    """
    try:
        data = request.json
        logger.info(f"📥 Initiate request: {data}")
        
        phone = data.get('phone')
        amount = data.get('amount')
        service = data.get('service', 'general')
        purpose = data.get('purpose', '')
        client_type = data.get('client_type', 'individual')
        reference = data.get('reference')
        user_id = data.get('user_id')
        callback_url = data.get('callback_url')
        
        if not phone or not amount or not reference:
            return jsonify({
                "success": False,
                "error": "Missing required fields: phone, amount, reference"
            }), 400
        
        formatted_phone = format_phone(phone)
        timestamp = generate_timestamp()
        password = generate_password(timestamp)
        access_token = get_mpesa_access_token()
        
        stk_push_payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": formatted_phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": formatted_phone,
            "CallBackURL": callback_url or f"{os.environ.get('BASE_URL', 'https://auto-v.onrender.com')}/api/mpesa/callback",
            "AccountReference": reference,
            "TransactionDesc": f"AUTO-V {service} - {purpose}"
        }
        
        logger.info(f"📤 Sending STK Push: {stk_push_payload}")
        
        with httpx.Client() as client:
            response = client.post(
                f"{MPESA_API_BASE}/mpesa/stkpush/v1/processrequest",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=stk_push_payload
            )
            
            if response.status_code != 200:
                logger.error(f"M-Pesa STK Push error: {response.text}")
                return jsonify({
                    "success": False,
                    "error": "M-Pesa STK Push failed"
                }), 500
            
            result = response.json()
            logger.info(f"📥 M-Pesa STK Response: {result}")
            
            checkout_request_id = result.get("CheckoutRequestID") or result.get("MerchantRequestID")
            if not checkout_request_id:
                return jsonify({
                    "success": False,
                    "error": "No CheckoutRequestID returned from M-Pesa"
                }), 500
            
            transaction_data = {
                "checkout_request_id": checkout_request_id,
                "phone": formatted_phone,
                "amount": int(amount),
                "service": service,
                "purpose": purpose,
                "client_type": client_type,
                "reference": reference,
                "user_id": user_id,
                "status": "pending",
                "mpesa_response": result,
                "created_at": datetime.datetime.now().isoformat()
            }
            
            supabase.table("mpesa_transactions").insert(transaction_data).execute()
            
            return jsonify({
                "success": True,
                "checkout_request_id": checkout_request_id,
                "MerchantRequestID": result.get("MerchantRequestID"),
                "ResponseCode": result.get("ResponseCode"),
                "ResponseDescription": result.get("ResponseDescription"),
                "data": {
                    "checkout_request_id": checkout_request_id,
                    "reference": reference,
                    "amount": int(amount)
                }
            })
            
    except Exception as e:
        logger.error(f"❌ M-Pesa initiate error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/mpesa/status/<checkout_request_id>', methods=['GET'])
def check_payment_status(checkout_request_id):
    """Check payment status by CheckoutRequestID"""
    try:
        if not checkout_request_id:
            return jsonify({
                "success": False,
                "error": "Missing checkout_request_id"
            }), 400
        
        result_data = supabase.table("mpesa_transactions") \
            .select("*") \
            .eq("checkout_request_id", checkout_request_id) \
            .maybe_single() \
            .execute()
        
        tx = result_data.data if hasattr(result_data, 'data') else result_data
        
        if not tx:
            logger.warning(f"⚠️ Transaction not found: {checkout_request_id}")
            return jsonify({
                "success": False,
                "error": "Transaction not found"
            }), 404
        
        status = tx.get("status", "pending")
        result_code = tx.get("mpesa_result_code")
        result_desc = tx.get("mpesa_result_desc")
        
        if status == "pending" and result_code:
            if result_code == "0" or result_code == "000":
                status = "completed"
            elif str(result_code) in ["1", "1037", "1032", "2001", "2002"]:
                status = "failed"
        
        return jsonify({
            "success": True,
            "checkout_request_id": checkout_request_id,
            "status": status,
            "payment_status": status,
            "result_code": result_code,
            "result_desc": result_desc,
            "amount": tx.get("amount"),
            "reference": tx.get("reference"),
            "data": {
                "checkout_request_id": checkout_request_id,
                "status": status,
                "result_code": result_code,
                "amount": tx.get("amount"),
                "reference": tx.get("reference")
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Status check failed"
        }), 500

@app.route('/api/mpesa/auto-confirm/<checkout_request_id>', methods=['POST'])
def auto_confirm_payment(checkout_request_id):
    """Auto-confirm payment by querying M-Pesa directly"""
    try:
        if not checkout_request_id:
            return jsonify({
                "success": False,
                "error": "Missing checkout_request_id"
            }), 400
        
        result_data = supabase.table("mpesa_transactions") \
            .select("*") \
            .eq("checkout_request_id", checkout_request_id) \
            .maybe_single() \
            .execute()
        
        tx = result_data.data if hasattr(result_data, 'data') else result_data
        
        if not tx:
            return jsonify({
                "success": False,
                "error": "Transaction not found"
            }), 404
        
        if tx.get("status") == "completed":
            return jsonify({
                "success": True,
                "result_code": "0",
                "status": "completed",
                "data": {
                    "checkout_request_id": checkout_request_id,
                    "status": "completed",
                    "result_code": "0",
                    "amount": tx.get("amount"),
                    "reference": tx.get("reference")
                }
            })
        
        try:
            access_token = get_mpesa_access_token()
            timestamp = generate_timestamp()
            password = generate_password(timestamp)
            
            query_payload = {
                "BusinessShortCode": MPESA_SHORTCODE,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            with httpx.Client() as client:
                response = client.post(
                    f"{MPESA_API_BASE}/mpesa/stkpushquery/v1/query",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=query_payload
                )
                
                if response.status_code != 200:
                    logger.error(f"M-Pesa Query error: {response.text}")
                    return jsonify({
                        "success": True,
                        "status": tx.get("status"),
                        "result_code": tx.get("mpesa_result_code"),
                        "result_desc": tx.get("mpesa_result_desc", "Unable to query M-Pesa"),
                        "data": {
                            "checkout_request_id": checkout_request_id,
                            "status": tx.get("status"),
                            "result_code": tx.get("mpesa_result_code"),
                            "amount": tx.get("amount"),
                            "reference": tx.get("reference")
                        }
                    })
                
                result = response.json()
                logger.info(f"📥 M-Pesa Query Response: {result}")
                
                result_code = result.get("ResultCode") or result.get("ResponseCode")
                result_desc = result.get("ResultDesc") or result.get("ResponseDescription")
                
                new_status = tx.get("status")
                if result_code == "0" or result_code == "000":
                    new_status = "completed"
                elif str(result_code) in ["1", "1037", "1032", "2001", "2002"]:
                    new_status = "failed"
                
                if new_status != tx.get("status"):
                    supabase.table("mpesa_transactions") \
                        .update({
                            "status": new_status,
                            "mpesa_result_code": str(result_code),
                            "mpesa_result_desc": result_desc,
                            "updated_at": datetime.datetime.now().isoformat()
                        }) \
                        .eq("checkout_request_id", checkout_request_id) \
                        .execute()
                
                return jsonify({
                    "success": True,
                    "result_code": result_code,
                    "result_desc": result_desc,
                    "status": new_status,
                    "data": {
                        "checkout_request_id": checkout_request_id,
                        "status": new_status,
                        "result_code": result_code,
                        "amount": tx.get("amount"),
                        "reference": tx.get("reference")
                    }
                })
                
        except Exception as mpesa_error:
            logger.error(f"❌ M-Pesa query error: {str(mpesa_error)}")
            return jsonify({
                "success": True,
                "status": tx.get("status"),
                "result_code": tx.get("mpesa_result_code"),
                "result_desc": tx.get("mpesa_result_desc", "Unable to query M-Pesa"),
                "data": {
                    "checkout_request_id": checkout_request_id,
                    "status": tx.get("status"),
                    "result_code": tx.get("mpesa_result_code"),
                    "amount": tx.get("amount"),
                    "reference": tx.get("reference")
                }
            })
        
    except Exception as e:
        logger.error(f"❌ Auto-confirm error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Auto-confirm failed"
        }), 500

@app.route('/api/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """M-Pesa Callback endpoint - receives payment confirmation"""
    try:
        body = request.json
        logger.info(f"📥 M-Pesa Callback Received")
        
        stk_callback = body.get("Body", {}).get("stkCallback")
        if not stk_callback:
            logger.warning("⚠️ Invalid callback format")
            return jsonify({"status": "OK"})
        
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        
        metadata_items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        amount = None
        mpesa_receipt = None
        phone = None
        
        for item in metadata_items:
            if item.get("Name") == "Amount":
                amount = item.get("Value")
            elif item.get("Name") == "MpesaReceiptNumber":
                mpesa_receipt = item.get("Value")
            elif item.get("Name") == "PhoneNumber":
                phone = item.get("Value")
        
        logger.info(f"✅ Callback: checkoutRequestId={checkout_request_id}, resultCode={result_code}")
        
        status = "pending"
        if result_code == "0" or result_code == "000":
            status = "completed"
        elif str(result_code) in ["1", "1037", "1032", "2001", "2002"]:
            status = "failed"
        
        update_data = {
            "status": status,
            "mpesa_result_code": str(result_code),
            "mpesa_result_desc": result_desc,
            "mpesa_receipt": mpesa_receipt,
            "mpesa_phone": phone,
            "mpesa_amount": amount,
            "callback_data": stk_callback,
            "updated_at": datetime.datetime.now().isoformat()
        }
        
        if checkout_request_id:
            supabase.table("mpesa_transactions") \
                .update(update_data) \
                .eq("checkout_request_id", checkout_request_id) \
                .execute()
        
        return jsonify({"status": "OK"})
        
    except Exception as e:
        logger.error(f"❌ Callback error: {str(e)}")
        return jsonify({"status": "OK"})

# ============================================================
# ENTRY POINT (FIXED)
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # ✅ Important: host='0.0.0.0' allows external access
    app.run(host='0.0.0.0', port=port, debug=False)
