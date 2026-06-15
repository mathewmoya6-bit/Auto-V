# ============================================
# AUTO-V BACKEND API
# Production: https://auto-v-backend.onrender.com
# ============================================

import os
import json
import time
import hmac
import hashlib
import base64
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# ============================================
# APP CONFIGURATION
# ============================================
app = FastAPI(
    title="AUTO-V API",
    description="Vehicle Valuation, Inspection, and Mileage Reimbursement API",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS Configuration - Allow frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://auto-v.meipressgroup.com",
        "https://auto-v.onrender.com",
        "http://localhost:3000",
        "http://localhost:5500",
        "*"  # For testing, restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# ============================================
# SUPABASE CONFIGURATION
# ============================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tsvejnzxrxrrecgquxbq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ")

# ============================================
# M-PESA CONFIGURATION
# ============================================
MPESA_CONFIG = {
    "CONSUMER_KEY": os.getenv("MPESA_CONSUMER_KEY", "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv"),
    "CONSUMER_SECRET": os.getenv("MPESA_CONSUMER_SECRET", "aGGo8AuPJVpsZLcs"),
    "PASSKEY": os.getenv("MPESA_PASSKEY", "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277"),
    "SHORTCODE": os.getenv("MPESA_SHORTCODE", "4095377"),
    "ENVIRONMENT": os.getenv("MPESA_ENVIRONMENT", "sandbox"),  # sandbox or production
}

# API endpoints
MPESA_API_URLS = {
    "sandbox": "https://sandbox.safaricom.co.ke",
    "production": "https://api.safaricom.co.ke"
}

# ============================================
# PYDANTIC MODELS
# ============================================

class MpesaSTKPushRequest(BaseModel):
    amount: int = Field(..., ge=10, le=150000)
    phone: str = Field(..., min_length=10, max_length=13)
    service_type: str
    user_id: str
    request_id: Optional[str] = None

class MpesaStatusRequest(BaseModel):
    checkoutRequestID: str

class ValuationRequest(BaseModel):
    make: str
    model: str
    year: int
    odometer: int
    condition: str
    accident_history: str
    registration_number: str
    purpose: str

class MileageClaimRequest(BaseModel):
    trip_date: str
    vehicle_category: str
    start_location: str
    end_location: str
    start_odometer: int
    end_odometer: int
    purpose: str
    notes: Optional[str] = ""

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_mpesa_api_url():
    env = MPESA_CONFIG["ENVIRONMENT"]
    return MPESA_API_URLS.get(env, MPESA_API_URLS["sandbox"])

async def get_mpesa_access_token():
    """Get OAuth token from M-Pesa API"""
    api_url = get_mpesa_api_url()
    consumer_key = MPESA_CONFIG["CONSUMER_KEY"]
    consumer_secret = MPESA_CONFIG["CONSUMER_SECRET"]
    
    auth = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{api_url}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            raise HTTPException(status_code=500, detail="Failed to get M-Pesa token")

def generate_mpesa_password():
    """Generate password for STK Push"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_str = f"{MPESA_CONFIG['SHORTCODE']}{MPESA_CONFIG['PASSKEY']}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()
    return password, timestamp

def format_phone_number(phone: str) -> str:
    """Format phone number to 254XXXXXXXXX format"""
    # Remove any non-digit characters
    phone = ''.join(filter(str.isdigit, phone))
    
    # If starts with 0, replace with 254
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    # If starts with +254, remove the +
    elif phone.startswith('254'):
        phone = phone
    elif phone.startswith('+'):
        phone = phone[1:]
    
    return phone

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {
        "message": "AUTO-V API is running",
        "version": "3.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "docs": "/api/docs",
            "health": "/api/health",
            "mpesa_stkpush": "/api/mpesa/stkpush",
            "mpesa_callback": "/api/mpesa/callback",
            "mpesa_status": "/api/mpesa/status",
            "valuation": "/api/valuation/calculate"
        }
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "auto-v-backend",
        "timestamp": datetime.now().isoformat(),
        "mpesa_env": MPESA_CONFIG["ENVIRONMENT"]
    }

# ============================================
# M-PESA STK PUSH ENDPOINTS
# ============================================

@app.post("/api/mpesa/stkpush")
async def mpesa_stkpush(request: MpesaSTKPushRequest):
    """
    Initiate M-Pesa STK Push (Lipa Na M-Pesa Online)
    Sends payment prompt to customer's phone
    """
    try:
        # Get access token
        access_token = await get_mpesa_access_token()
        
        # Format phone number
        phone_number = format_phone_number(request.phone)
        
        # Generate password and timestamp
        password, timestamp = generate_mpesa_password()
        
        # Prepare request body
        api_url = get_mpesa_api_url()
        callback_url = f"https://auto-v.onrender.com/api/mpesa/callback"
        
        # For testing with sandbox, use a test callback URL
        if MPESA_CONFIG["ENVIRONMENT"] == "sandbox":
            callback_url = "https://webhook.site/8f8e8b1c-6f6a-4d3e-9a1c-5b3f2e8d9a7c"
        
        body = {
            "BusinessShortCode": MPESA_CONFIG["SHORTCODE"],
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": request.amount,
            "PartyA": phone_number,
            "PartyB": MPESA_CONFIG["SHORTCODE"],
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": f"AUTOV-{int(time.time())}",
            "TransactionDesc": f"{request.service_type.upper()} Payment"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/mpesa/stkpush/v1/processrequest",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=body
            )
            
            result = response.json()
            
            if result.get("ResponseCode") == "0":
                return {
                    "success": True,
                    "checkoutRequestID": result.get("CheckoutRequestID"),
                    "merchantRequestID": result.get("MerchantRequestID"),
                    "message": "Payment initiated. Check your phone for M-Pesa prompt."
                }
            else:
                return {
                    "success": False,
                    "error": result.get("errorMessage") or result.get("ResponseDescription", "Payment initiation failed")
                }
                
    except Exception as e:
        print(f"STK Push error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mpesa/callback")
async def mpesa_callback(request: Request):
    """
    M-Pesa STK Push Callback URL
    Receives payment confirmation from Safaricom
    """
    try:
        callback_data = await request.json()
        print(f"M-Pesa Callback received: {json.dumps(callback_data, indent=2)}")
        
        # Extract callback details
        body = callback_data.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        
        # Extract metadata if payment successful
        metadata = {}
        if result_code == 0:
            callback_metadata = stk_callback.get("CallbackMetadata", {})
            for item in callback_metadata.get("Item", []):
                metadata[item.get("Name")] = item.get("Value")
        
        # Log the payment result
        payment_status = "completed" if result_code == 0 else "failed"
        
        # Here you would update your database:
        # - Update transaction status
        # - Update service request payment status
        # - Send confirmation email to user
        
        print(f"Payment {payment_status}: {checkout_request_id} - {result_desc}")
        if metadata:
            print(f"Receipt: {metadata.get('MpesaReceiptNumber')}")
            print(f"Amount: {metadata.get('Amount')}")
        
        return {"ResultCode": 0, "ResultDesc": "Success"}
        
    except Exception as e:
        print(f"Callback error: {str(e)}")
        return {"ResultCode": 1, "ResultDesc": str(e)}

@app.post("/api/mpesa/status")
async def mpesa_status(request: MpesaStatusRequest):
    """
    Query STK Push Status
    Check if a payment has been completed
    """
    try:
        access_token = await get_mpesa_access_token()
        password, timestamp = generate_mpesa_password()
        api_url = get_mpesa_api_url()
        
        body = {
            "BusinessShortCode": MPESA_CONFIG["SHORTCODE"],
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": request.checkoutRequestID
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/mpesa/stkpushquery/v1/query",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=body
            )
            
            result = response.json()
            
            # ResultCode 0 = Success, 1037 = Pending, 1032 = Failed
            result_code = result.get("ResultCode")
            
            if result_code == "0":
                return {"status": "completed", "message": result.get("ResultDesc")}
            elif result_code == "1037":
                return {"status": "pending", "message": result.get("ResultDesc")}
            else:
                return {"status": "failed", "message": result.get("ResultDesc")}
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# VALUATION ENGINE
# ============================================

@app.post("/api/valuation/calculate")
async def calculate_valuation(request: ValuationRequest):
    """Calculate vehicle valuation based on inputs"""
    
    age = datetime.now().year - request.year
    
    # Base values by make
    base_values = {
        'toyota': 2800000,
        'mercedes': 5000000,
        'bmw': 4500000,
        'honda': 2500000,
        'nissan': 2300000,
        'mazda': 2200000,
        'subaru': 2600000,
        'volkswagen': 2400000,
        'hyundai': 2000000,
        'ford': 2100000
    }
    
    base_value = base_values.get(request.make.lower(), 2000000)
    
    # Calculate factors
    age_factor = max(0.35, 1 - (age * 0.08))
    mileage_factor = max(0.45, 1 - (request.odometer / 300000))
    
    condition_factors = {
        'Excellent': 1.15,
        'Good': 1.0,
        'Fair': 0.85,
        'Poor': 0.7
    }
    condition_factor = condition_factors.get(request.condition, 1.0)
    
    accident_factors = {
        'None': 1.0,
        'Minor': 0.85,
        'Moderate': 0.65,
        'Major': 0.4
    }
    accident_factor = accident_factors.get(request.accident_history, 1.0)
    
    # Calculate market value
    market_value = int(base_value * age_factor * mileage_factor * condition_factor * accident_factor)
    market_value = max(150000, min(market_value, base_value * 1.2))
    
    # Generate certificate number
    certificate_number = f"AUTO-{int(time.time())}-{os.urandom(4).hex().upper()}"
    
    return {
        "success": True,
        "market_value": market_value,
        "insurance_value": int(market_value * 1.1),
        "trade_in_value": int(market_value * 0.8),
        "forced_sale_value": int(market_value * 0.7),
        "certificate_number": certificate_number,
        "valuation_date": datetime.now().isoformat()
    }

# ============================================
# MILEAGE CLAIM ENGINE
# ============================================

@app.post("/api/mileage/calculate")
async def calculate_mileage(request: MileageClaimRequest):
    """Calculate mileage claim amount"""
    
    # Distance calculation
    distance = request.end_odometer - request.start_odometer
    
    if distance <= 0:
        raise HTTPException(status_code=400, detail="End odometer must be greater than start odometer")
    
    # Rate per KM by vehicle category
    rates = {
        'Small Hatchback': 22,
        'Compact Sedan': 28,
        'Midsize Sedan': 35,
        'SUV/Crossover': 42,
        'Large SUV': 55,
        'Pickup Truck': 48,
        'Minibus': 65,
        'Motorcycle': 12
    }
    
    rate = rates.get(request.vehicle_category, 28)
    amount = distance * rate
    
    return {
        "success": True,
        "distance_km": distance,
        "rate_per_km": rate,
        "claim_amount": amount,
        "currency": "KES"
    }

# ============================================
# MILEAGE RATES ENDPOINT
# ============================================

@app.get("/api/mileage/rates")
async def get_mileage_rates():
    """Get current mileage rates"""
    rates = {
        "Small Hatchback": 22,
        "Compact Sedan": 28,
        "Midsize Sedan": 35,
        "SUV/Crossover": 42,
        "Large SUV": 55,
        "Pickup Truck": 48,
        "Minibus": 65,
        "Motorcycle": 12,
        "Three-Wheeler": 15
    }
    
    return {
        "success": True,
        "rates": rates,
        "updated_at": datetime.now().isoformat()
    }

# ============================================
# SERVER START (for local testing)
# ============================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
