# app.py
# AUTO-V Backend - M-Pesa + AI Valuation Engine
# Flask version - Production ready for Render

import os
import base64
import json
import datetime
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================
load_dotenv()

# ============================================================
# LOGGING SETUP
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG & SECURITY CHECKS
# ============================================================
app = Flask(__name__)

# ✅ PRODUCTION CORS - Restrict to your frontend domains
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "https://auto-v.meipressgroup.com",
                "https://www.auto-v.meipressgroup.com"
            ],
            "supports_credentials": True
        }
    }
)

# ✅ GLOBAL AFTER REQUEST HEADER HANDLER
# This guarantees CORS headers on every single response
@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = request.headers.get('Origin', '*')
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response

# ============================================================
# SECURE ENVIRONMENT VARIABLE LOADING
# ✅ Keys must be set in Render Environment Variables
# ============================================================

# 1. Supabase (Must be set in Render ENV)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    logger.critical("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in environment!")
    # App will still run but Supabase features will fail

# 2. M-Pesa (Must be set in Render ENV)
MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET")
MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY")
MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "4095377")
MPESA_ENVIRONMENT = os.environ.get("MPESA_ENVIRONMENT", "sandbox")

if not MPESA_CONSUMER_KEY or not MPESA_CONSUMER_SECRET or not MPESA_PASSKEY:
    logger.critical("❌ M-Pesa credentials missing from environment variables!")
    # App will still run but M-Pesa features will fail

# ============================================================
# INITIALIZE CLIENTS
# ============================================================

# Create Supabase client safely
supabase = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("✅ Supabase connected successfully")
    except Exception as e:
        logger.error(f"❌ Supabase connection error: {e}")
        supabase = None

# Base URL for M-Pesa API
MPESA_API_BASE = "https://api.safaricom.co.ke" if MPESA_ENVIRONMENT == "production" else "https://sandbox.safaricom.co.ke"

# ============================================================
# UTILITY FUNCTIONS (M-PESA)
# ============================================================

def generate_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

def generate_password(timestamp: str) -> str:
    data = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
    return base64.b64encode(data.encode()).decode()

def format_phone(phone: str) -> str:
    cleaned = ''.join(c for c in phone if c.isdigit())
    if cleaned.startswith('0'):
        cleaned = '254' + cleaned[1:]
    elif cleaned.startswith('7') and len(cleaned) == 9:
        cleaned = '254' + cleaned
    elif len(cleaned) == 10 and cleaned.startswith('07'):
        cleaned = '254' + cleaned[1:]
    return cleaned

def get_mpesa_access_token() -> str:
    auth_str = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
    auth_bytes = auth_str.encode()
    auth_b64 = base64.b64encode(auth_bytes).decode()
    
    response = requests.get(
        f"{MPESA_API_BASE}/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {auth_b64}"},
        timeout=30
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to get M-Pesa access token: {response.text}")
        raise Exception("M-Pesa authentication failed")
    
    return response.json()["access_token"]

# ============================================================
# AI VALUATION ENGINE DATA
# ============================================================

CAR_BASE_PRICES = {
    'Toyota': 2800000, 'Nissan': 2300000, 'BMW': 4500000,
    'Mercedes': 5000000, 'Honda': 2500000, 'Mazda': 2200000,
    'Volkswagen': 2400000, 'Mitsubishi': 2100000, 'Subaru': 2600000,
    'Ford': 2100000, 'Chevrolet': 2000000, 'Jeep': 3500000,
    'Land Rover': 4000000, 'Hyundai': 2200000, 'Kia': 2100000,
    'Peugeot': 2000000, 'Suzuki Car': 1800000, 'Isuzu': 2500000,
    'Daihatsu': 1600000, 'Other': 2000000
}

BIKE_BASE_PRICES = {
    'Honda Bike': 350000, 'Yamaha': 380000, 'Suzuki Bike': 320000,
    'Kawasaki': 450000, 'TVS': 200000, 'Bajaj': 180000,
    'Hero': 160000, 'Royal Enfield': 600000, 'KTM': 500000,
    'Aprilia': 400000, 'BMW Motorrad': 700000, 'Ducati': 650000,
    'Triumph': 550000, 'Harley Davidson': 800000, 'MV Agusta': 600000,
    'Other Bike': 250000
}

TRICYCLE_BASE_PRICES = {
    'Piaggio': 450000, 'TVS Tricycle': 350000, 'Bajaj Tricycle': 380000,
    'Other Tricycle': 300000
}

# Consolidated Base Prices
BASE_PRICES = {**CAR_BASE_PRICES, **BIKE_BASE_PRICES, **TRICYCLE_BASE_PRICES}

# Model Multipliers
CAR_MODEL_MULTIPLIERS = {
    'land cruiser': 1.45, 'prado': 1.35, 'hilux': 1.20, 'corolla': 0.90,
    'axio': 0.90, 'fielder': 0.95, 'voxy': 1.05, 'noah': 1.05, 'hiace': 1.10,
    'rav4': 1.15, 'harrier': 1.10, 'alphard': 1.25, 'vellfire': 1.25,
    'camry': 1.00, 'premio': 1.00, 'allion': 1.00, 'estima': 1.05,
    'fortuner': 1.20,
    'x-trail': 1.15, 'patrol': 1.30, 'navara': 1.10, 'note': 0.80,
    'juke': 1.00, 'qashqai': 1.10, 'pathfinder': 1.15,
    'x5': 1.25, 'x3': 1.15, '3 series': 1.10, '5 series': 1.10,
    '7 series': 1.20,
    'c-class': 1.10, 'e-class': 1.25, 'g-class': 1.50, 'glc': 1.15,
    'gle': 1.20, 's-class': 1.30,
    'cr-v': 1.15, 'accord': 1.10, 'fit': 0.85, 'civic': 1.00,
    'hr-v': 1.05, 'vezel': 1.05,
    'cx-5': 1.15, 'demio': 0.85, 'atenza': 1.00, 'cx-3': 1.05,
    'golf': 1.10, 'polo': 0.95, 'tiguan': 1.10, 'passat': 1.00,
    'pajero': 1.15, 'lancer': 0.90, 'asx': 1.00, 'outlander': 1.10,
    'forester': 1.10, 'outback': 1.15, 'legacy': 1.10, 'impreza': 1.00,
    'ranger': 1.20, 'mustang': 1.15, 'everest': 1.15, 'focus': 1.00,
    'wrangler': 1.15, 'range rover': 1.45, 'defender': 1.30,
    'santa fe': 1.05, 'tucson': 1.00, 'sportage': 1.05, 'sorento': 1.10,
    '3008': 1.05, '5008': 1.10, 'swift': 0.95, 'vitara': 1.00,
    'd-max': 1.10, 'terios': 0.95
}

BIKE_MODEL_MULTIPLIERS = {
    'cbr': 1.20, 'cb500': 1.10, 'africa twin': 1.40,
    'r1': 1.20, 'r6': 1.10, 'mt-07': 1.00, 'tenere': 1.25,
    'gsx-r': 1.15, 'v-strom': 1.10,
    'ninja': 1.20, 'z900': 1.15, 'versys': 1.10,
    'classic 350': 1.00, 'himalayan': 1.10, 'continental gt': 1.00,
    'duke': 1.05, 'rc': 1.10, 'adventure': 1.15,
    'pulsar': 1.00, 'dominor': 1.05,
    'apache': 1.05
}

TRICYCLE_MODEL_MULTIPLIERS = {'ape': 1.10, 'auto': 1.00, 'tuk tuk': 1.00}

MODEL_MULTIPLIERS = {**CAR_MODEL_MULTIPLIERS, **BIKE_MODEL_MULTIPLIERS, **TRICYCLE_MODEL_MULTIPLIERS}

# Factor Tables
CONDITION_FACTORS = {'Excellent': 1.15, 'Good': 1.0, 'Fair': 0.85, 'Poor': 0.65}
ACCIDENT_FACTORS = {'None': 1.0, 'Minor': 0.9, 'Major': 0.65, 'WriteOff': 0.4}
LOCATION_FACTORS = {'Nairobi': 1.10, 'Mombasa': 1.05, 'Kisumu': 0.95, 'Nakuru': 0.95, 'Eldoret': 0.95, 'Thika': 1.00, 'Malindi': 0.90, 'Other': 1.00}
FUEL_FACTORS = {'Petrol': 1.0, 'Diesel': 0.95, 'Hybrid': 1.12, 'Electric': 1.15}
TRANSMISSION_FACTORS = {'Automatic': 1.05, 'Manual': 1.0, 'CVT': 1.08}
USAGE_FACTORS = {'Personal': 1.0, 'Commercial': 0.85}

def get_ownership_factor(owners: int) -> float:
    if owners == 0: return 1.05
    if owners == 1: return 1.00
    if owners <= 3: return 0.90
    if owners <= 5: return 0.80
    return 0.65

# ============================================================
# ROUTES: M-PESA
# ============================================================

@app.route('/', methods=['GET'])
def root():
    return jsonify({"message": "AUTO-V Backend is running"})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat()
    })

@app.route('/api/mpesa/initiate', methods=['POST'])
def initiate_payment():
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
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
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
        
        response = requests.post(
            f"{MPESA_API_BASE}/mpesa/stkpush/v1/processrequest",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=stk_push_payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"M-Pesa STK Push error: {response.text}")
            return jsonify({"success": False, "error": f"STK Push failed: {response.text}"}), 500
        
        result = response.json()
        logger.info(f"📥 M-Pesa STK Response: {result}")
        
        checkout_request_id = result.get("CheckoutRequestID") or result.get("MerchantRequestID")
        if not checkout_request_id:
            return jsonify({"success": False, "error": "No CheckoutRequestID returned"}), 500
        
        if supabase:
            supabase.table("mpesa_transactions").insert({
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
            }).execute()
        
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
        
    except requests.exceptions.Timeout:
        logger.error("❌ M-Pesa request timed out")
        return jsonify({"success": False, "error": "M-Pesa request timed out"}), 504
    except Exception as e:
        logger.error(f"❌ M-Pesa initiate error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/mpesa/status/<checkout_request_id>', methods=['GET'])
def check_payment_status(checkout_request_id):
    try:
        if not checkout_request_id:
            return jsonify({"success": False, "error": "Missing checkout_request_id"}), 400
        
        if not supabase:
            return jsonify({"success": False, "error": "Supabase not available"}), 500
        
        tx = supabase.table("mpesa_transactions").select("*").eq("checkout_request_id", checkout_request_id).maybe_single().execute()
        tx = tx.data if hasattr(tx, 'data') else tx
        
        if not tx:
            return jsonify({"success": False, "error": "Transaction not found"}), 404
        
        status = tx.get("status", "pending")
        result_code = tx.get("mpesa_result_code")
        
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
            "result_desc": tx.get("mpesa_result_desc"),
            "amount": tx.get("amount"),
            "reference": tx.get("reference")
        })
        
    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
        return jsonify({"success": False, "error": "Status check failed"}), 500

@app.route('/api/mpesa/auto-confirm/<checkout_request_id>', methods=['POST'])
def auto_confirm_payment(checkout_request_id):
    try:
        if not checkout_request_id:
            return jsonify({"success": False, "error": "Missing checkout_request_id"}), 400
        
        if not supabase:
            return jsonify({"success": False, "error": "Supabase not available"}), 500
        
        tx = supabase.table("mpesa_transactions").select("*").eq("checkout_request_id", checkout_request_id).maybe_single().execute()
        tx = tx.data if hasattr(tx, 'data') else tx
        
        if not tx:
            return jsonify({"success": False, "error": "Transaction not found"}), 404
        
        if tx.get("status") == "completed":
            return jsonify({"success": True, "result_code": "0", "status": "completed", "data": {}})
        
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
            
            response = requests.post(
                f"{MPESA_API_BASE}/mpesa/stkpushquery/v1/query",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json=query_payload,
                timeout=30
            )
            
            if response.status_code != 200:
                return jsonify({"success": True, "status": tx.get("status"), "result_code": tx.get("mpesa_result_code"), "result_desc": "Unable to query M-Pesa"})
            
            result = response.json()
            result_code = result.get("ResultCode") or result.get("ResponseCode")
            result_desc = result.get("ResultDesc") or result.get("ResponseDescription")
            
            new_status = tx.get("status")
            if result_code == "0" or result_code == "000":
                new_status = "completed"
            elif str(result_code) in ["1", "1037", "1032", "2001", "2002"]:
                new_status = "failed"
            
            if new_status != tx.get("status"):
                supabase.table("mpesa_transactions").update({
                    "status": new_status,
                    "mpesa_result_code": str(result_code),
                    "mpesa_result_desc": result_desc,
                    "updated_at": datetime.datetime.now().isoformat()
                }).eq("checkout_request_id", checkout_request_id).execute()
            
            return jsonify({"success": True, "result_code": result_code, "result_desc": result_desc, "status": new_status})
            
        except Exception as mpesa_error:
            logger.error(f"❌ M-Pesa query error: {str(mpesa_error)}")
            return jsonify({"success": True, "status": tx.get("status"), "result_code": tx.get("mpesa_result_code")})
        
    except Exception as e:
        logger.error(f"❌ Auto-confirm error: {str(e)}")
        return jsonify({"success": False, "error": "Auto-confirm failed"}), 500

@app.route('/api/mpesa/callback', methods=['POST'])
def mpesa_callback():
    try:
        body = request.json
        logger.info("📥 M-Pesa Callback Received")
        
        stk_callback = body.get("Body", {}).get("stkCallback")
        if not stk_callback:
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
        
        status = "pending"
        if result_code == "0" or result_code == "000":
            status = "completed"
        elif str(result_code) in ["1", "1037", "1032", "2001", "2002"]:
            status = "failed"
        
        if supabase and checkout_request_id:
            supabase.table("mpesa_transactions").update({
                "status": status,
                "mpesa_result_code": str(result_code),
                "mpesa_result_desc": result_desc,
                "mpesa_receipt": mpesa_receipt,
                "mpesa_phone": phone,
                "mpesa_amount": amount,
                "callback_data": stk_callback,
                "updated_at": datetime.datetime.now().isoformat()
            }).eq("checkout_request_id", checkout_request_id).execute()
        
        return jsonify({"status": "OK"})
        
    except Exception as e:
        logger.error(f"❌ Callback error: {str(e)}")
        return jsonify({"status": "OK"})

# ============================================================
# ROUTES: AI VALUATION ENGINE
# ============================================================

@app.route('/instant-check/valuate', methods=['POST'])
def calculate_instant_value():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        make = data.get('make')
        model = data.get('model')
        year = data.get('year')
        mileage = data.get('mileage')
        fuel_type = data.get('fuel_type')
        transmission = data.get('transmission')
        condition = data.get('condition')
        accident_history = data.get('accident_history')
        location = data.get('location')
        previous_owners = data.get('previous_owners', 0)
        usage_type = data.get('usage_type', 'Personal')
        vehicle_type = data.get('vehicle_type', 'Car')

        if not all([make, model, year, mileage, fuel_type, transmission, condition, accident_history, location]):
            return jsonify({"success": False, "error": "Missing required parameters"}), 400

        try:
            year = int(year)
            mileage = int(mileage)
            previous_owners = int(previous_owners)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Year, mileage, and previous_owners must be integers"}), 400

        current_year = datetime.datetime.now().year
        if year < 1990 or year > current_year + 1:
            return jsonify({"success": False, "error": f"Invalid year: {year}"}), 400
        if mileage < 0:
            return jsonify({"success": False, "error": "Mileage cannot be negative"}), 400

        base_price_key = make
        if vehicle_type.lower() == "bike" and "Bike" not in base_price_key:
            base_price_key = f"{make} Bike"
        elif vehicle_type.lower() == "tricycle" and "Tricycle" not in base_price_key:
            base_price_key = f"{make} Tricycle"
        
        value = BASE_PRICES.get(base_price_key, 2000000)
        model_key = model.lower().strip()
        model_multiplier = MODEL_MULTIPLIERS.get(model_key, 1.0)
        value = value * model_multiplier

        age = max(0, current_year - year)
        age_factor = max(0.35, min(1.0, 1 - (age * 0.07)))
        mileage_factor = max(0.45, min(1.0, 1 - (mileage / 300000)))
        condition_factor = CONDITION_FACTORS.get(condition, 1.0)
        accident_factor = ACCIDENT_FACTORS.get(accident_history, 1.0)
        location_factor = LOCATION_FACTORS.get(location, 1.0)
        fuel_factor = FUEL_FACTORS.get(fuel_type, 1.0)
        transmission_factor = TRANSMISSION_FACTORS.get(transmission, 1.0)
        usage_factor = USAGE_FACTORS.get(usage_type, 1.0)
        ownership_factor = get_ownership_factor(previous_owners)

        final_value = (
            value
            * age_factor
            * mileage_factor
            * condition_factor
            * accident_factor
            * location_factor
            * fuel_factor
            * transmission_factor
            * usage_factor
            * ownership_factor
        )

        final_value = round(final_value / 1000) * 1000
        final_value = max(150000, min(final_value, 8000000))

        return jsonify({
            "success": True,
            "value": int(final_value),
            "breakdown": {
                "base_price": int(value),
                "model_multiplier": round(model_multiplier, 2),
                "age_factor": round(age_factor, 2),
                "mileage_factor": round(mileage_factor, 2),
                "condition_factor": round(condition_factor, 2),
                "accident_factor": round(accident_factor, 2),
                "location_factor": round(location_factor, 2),
                "fuel_factor": round(fuel_factor, 2),
                "transmission_factor": round(transmission_factor, 2),
                "usage_factor": round(usage_factor, 2),
                "ownership_factor": round(ownership_factor, 2)
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Valuation engine error: {str(e)}"}), 500

# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
