# ============================================
# AUTO-V BACKEND API
# Production: https://auto-v.onrender.com
# ============================================

import os
import json
import time
import base64
import hmac
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import httpx

load_dotenv()

# ============================================
# APP CONFIGURATION
# ============================================
app = FastAPI(
    title="AUTO-V API",
    description="Vehicle Valuation, Inspection, and Mileage Reimbursement API",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://auto-v.meipressgroup.com", "https://auto-v.onrender.com", "http://localhost:5500", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# M-PESA CONFIGURATION
# ============================================
MPESA_CONFIG = {
    "CONSUMER_KEY": os.getenv("MPESA_CONSUMER_KEY", "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv"),
    "CONSUMER_SECRET": os.getenv("MPESA_CONSUMER_SECRET", "aGGo8AuPJVpsZLcs"),
    "PASSKEY": os.getenv("MPESA_PASSKEY", "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277"),
    "SHORTCODE": os.getenv("MPESA_SHORTCODE", "4095377"),
    "ENVIRONMENT": os.getenv("MPESA_ENVIRONMENT", "sandbox"),
}

MPESA_API_URLS = {
    "sandbox": "https://sandbox.safaricom.co.ke",
    "production": "https://api.safaricom.co.ke"
}

# ============================================
# MODELS
# ============================================
class MpesaSTKPushRequest(BaseModel):
    amount: int = Field(..., ge=10, le=150000)
    phone: str = Field(..., min_length=10, max_length=13)
    service_type: str
    user_id: str
    request_id: Optional[str] = None

class ValuationRequest(BaseModel):
    make: str
    model: str
    year: int
    odometer: int
    condition: str
    accident_history: str
    registration_number: str
    purpose: str = "Market Value"

class MileageRequest(BaseModel):
    trip_date: str
    vehicle_category: str
    start_location: str
    end_location: str
    start_odometer: int
    end_odometer: int
    purpose: str
    notes: Optional[str] = ""

# ============================================
# HELPERS
# ============================================
def get_mpesa_api_url():
    env = MPESA_CONFIG["ENVIRONMENT"]
    return MPESA_API_URLS.get(env, MPESA_API_URLS["sandbox"])

async def get_mpesa_access_token():
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
        raise HTTPException(status_code=500, detail="Failed to get M-Pesa token")

def generate_mpesa_password():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_str = f"{MPESA_CONFIG['SHORTCODE']}{MPESA_CONFIG['PASSKEY']}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()
    return password, timestamp

def format_phone(phone: str) -> str:
    phone = ''.join(filter(str.isdigit, phone))
    if phone.startswith('0'):
        return '254' + phone[1:]
    if phone.startswith('+'):
        return phone[1:]
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
            "valuation": "/api/valuation/calculate",
            "mileage": "/api/mileage/calculate"
        }
    }

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "auto-v-backend", "mpesa_env": MPESA_CONFIG["ENVIRONMENT"]}

# ============================================
# M-PESA STK PUSH
# ============================================
@app.post("/api/mpesa/stkpush")
async def mpesa_stkpush(request: MpesaSTKPushRequest):
    try:
        token = await get_mpesa_access_token()
        phone = format_phone(request.phone)
        password, timestamp = generate_mpesa_password()
        api_url = get_mpesa_api_url()
        
        body = {
            "BusinessShortCode": MPESA_CONFIG["SHORTCODE"],
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": request.amount,
            "PartyA": phone,
            "PartyB": MPESA_CONFIG["SHORTCODE"],
            "PhoneNumber": phone,
            "CallBackURL": "https://auto-v.onrender.com/api/mpesa/callback",
            "AccountReference": f"AUTOV-{int(time.time())}",
            "TransactionDesc": f"{request.service_type.upper()} Payment"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/mpesa/stkpush/v1/processrequest",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body
            )
            result = response.json()
            
            if result.get("ResponseCode") == "0":
                return {"success": True, "checkoutRequestID": result.get("CheckoutRequestID"), "message": "Payment initiated"}
            return {"success": False, "error": result.get("errorMessage", "Payment failed")}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/mpesa/callback")
async def mpesa_callback(request: Request):
    try:
        data = await request.json()
        print(f"M-Pesa Callback: {json.dumps(data, indent=2)}")
        stk = data.get("Body", {}).get("stkCallback", {})
        result_code = stk.get("ResultCode")
        checkout_id = stk.get("CheckoutRequestID")
        
        if result_code == 0:
            metadata = {}
            for item in stk.get("CallbackMetadata", {}).get("Item", []):
                metadata[item.get("Name")] = item.get("Value")
            print(f"✅ Payment successful: {metadata.get('MpesaReceiptNumber')}")
        else:
            print(f"❌ Payment failed: {stk.get('ResultDesc')}")
        
        return {"ResultCode": 0, "ResultDesc": "Success"}
    except Exception as e:
        return {"ResultCode": 1, "ResultDesc": str(e)}

@app.post("/api/mpesa/status")
async def mpesa_status(checkoutRequestID: str):
    return {"status": "pending", "message": "Check your phone for M-Pesa prompt"}

# ============================================
# VALUATION ENGINE
# ============================================
@app.post("/api/valuation/calculate")
async def calculate_valuation(request: ValuationRequest):
    age = datetime.now().year - request.year
    base_values = {'toyota': 2800000, 'mercedes': 5000000, 'bmw': 4500000, 'honda': 2500000, 'nissan': 2300000}
    base_value = base_values.get(request.make.lower(), 2000000)
    
    age_factor = max(0.35, 1 - (age * 0.08))
    mileage_factor = max(0.45, 1 - (request.odometer / 300000))
    condition_factors = {'Excellent': 1.15, 'Good': 1.0, 'Fair': 0.85, 'Poor': 0.7}
    condition_factor = condition_factors.get(request.condition, 1.0)
    accident_factors = {'None': 1.0, 'Minor': 0.85, 'Moderate': 0.65, 'Major': 0.4}
    accident_factor = accident_factors.get(request.accident_history, 1.0)
    
    market_value = int(base_value * age_factor * mileage_factor * condition_factor * accident_factor)
    market_value = max(150000, min(market_value, base_value * 1.2))
    
    return {
        "success": True,
        "market_value": market_value,
        "insurance_value": int(market_value * 1.1),
        "trade_in_value": int(market_value * 0.8),
        "forced_sale_value": int(market_value * 0.7),
        "certificate_number": f"AUTO-{int(time.time())}-{os.urandom(4).hex().upper()}"
    }

# ============================================
# MILEAGE ENGINE
# ============================================
@app.post("/api/mileage/calculate")
async def calculate_mileage(request: MileageRequest):
    distance = request.end_odometer - request.start_odometer
    if distance <= 0:
        raise HTTPException(status_code=400, detail="End odometer must be greater than start")
    
    rates = {'Small Hatchback': 22, 'Compact Sedan': 28, 'Midsize Sedan': 35, 'SUV/Crossover': 42, 'Large SUV': 55, 'Pickup Truck': 48, 'Minibus': 65, 'Motorcycle': 12}
    rate = rates.get(request.vehicle_category, 28)
    
    return {"success": True, "distance_km": distance, "rate_per_km": rate, "claim_amount": distance * rate, "currency": "KES"}

# ============================================
# RUN SERVER
# ============================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
