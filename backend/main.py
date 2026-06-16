# ============================================
# AUTO-V PRODUCTION BACKEND API
# Environment: PRODUCTION
# ============================================

import os, json, time, base64, uuid, logging
from datetime import datetime, date
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
import httpx

# Load environment
load_dotenv()

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AUTO-V API",
    description="Vehicle Valuation, Inspection, and Mileage Reimbursement API",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)
security = HTTPBearer()

# Production CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://auto-v.meipressgroup.com",
        "https://auto-v.onrender.com",
        "https://auto-v-backend.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# M-PESA PRODUCTION CONFIGURATION
# ============================================
MPESA = {
    "CONSUMER_KEY": os.getenv("MPESA_CONSUMER_KEY", "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv"),
    "CONSUMER_SECRET": os.getenv("MPESA_CONSUMER_SECRET", "aGGo8AuPJVpsZLcs"),
    "PASSKEY": os.getenv("MPESA_PASSKEY", "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277"),
    "SHORTCODE": os.getenv("MPESA_SHORTCODE", "4095377"),
    "ENVIRONMENT": "production",  # ← PRODUCTION MODE
}
MPESA_URLS = {
    "sandbox": "https://sandbox.safaricom.co.ke",
    "production": "https://api.safaricom.co.ke"
}

logger.info(f"M-Pesa Environment: {MPESA['ENVIRONMENT']}")

# ============================================
# MODELS
# ============================================
class ValuationRequest(BaseModel):
    make: str
    model: str
    year: int = Field(ge=1950, le=datetime.now().year)
    odometer: int = Field(ge=0)
    condition: str = Field(..., pattern="^(Excellent|Good|Fair|Poor)$")
    accident_history: str = Field(..., pattern="^(None|Minor|Moderate|Major)$")
    registration_number: str
    purpose: str = "Market Value"

class MileageRequest(BaseModel):
    trip_date: str
    vehicle_category: str
    start_location: str
    end_location: str
    start_odometer: int = Field(ge=0)
    end_odometer: int = Field(ge=0)
    purpose: str
    notes: Optional[str] = ""

    @validator('end_odometer')
    def validate_odometer(cls, v, values):
        if 'start_odometer' in values and v <= values['start_odometer']:
            raise ValueError('End odometer must be greater than start')
        return v

class MpesaRequest(BaseModel):
    amount: int = Field(ge=10, le=150000)
    phone: str
    service_type: str
    user_id: str
    request_id: Optional[str] = None

# ============================================
# HELPERS
# ============================================
def get_mpesa_url():
    return MPESA_URLS.get(MPESA["ENVIRONMENT"], MPESA_URLS["production"])

async def get_mpesa_token():
    url = get_mpesa_url()
    auth = base64.b64encode(f"{MPESA['CONSUMER_KEY']}:{MPESA['CONSUMER_SECRET']}".encode()).decode()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{url}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth}"}
        )
        if r.status_code == 200:
            return r.json().get("access_token")
        logger.error(f"M-Pesa token error: {r.text}")
        raise HTTPException(500, "Failed to get M-Pesa token")

def generate_mpesa_password():
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    pwd = base64.b64encode(f"{MPESA['SHORTCODE']}{MPESA['PASSKEY']}{ts}".encode()).decode()
    return pwd, ts

def format_phone(phone: str) -> str:
    phone = ''.join(filter(str.isdigit, phone))
    if phone.startswith('0'): return '254' + phone[1:]
    if phone.startswith('+'): return phone[1:]
    return phone

# ============================================
# ROOT & HEALTH
# ============================================
@app.get("/")
async def root():
    return {
        "message": "AUTO-V API",
        "version": "3.0.0",
        "status": "healthy",
        "environment": "production",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "auto-v-backend",
        "environment": "production",
        "mpesa_env": MPESA["ENVIRONMENT"]
    }

# ============================================
# VALUATION ENGINE
# ============================================
@app.post("/api/valuation/calculate")
async def calculate_valuation(req: ValuationRequest):
    logger.info(f"Valuation request: {req.make} {req.model} ({req.year})")
    age = datetime.now().year - req.year
    base = {'toyota': 2800000, 'mercedes': 5000000, 'bmw': 4500000, 'honda': 2500000, 'nissan': 2300000, 'subaru': 2600000}
    base_value = base.get(req.make.lower(), 2000000)
    age_factor = max(0.35, 1 - age * 0.08)
    mileage_factor = max(0.45, 1 - req.odometer / 300000)
    cond = {'Excellent': 1.15, 'Good': 1.0, 'Fair': 0.85, 'Poor': 0.7}
    acc = {'None': 1.0, 'Minor': 0.85, 'Moderate': 0.65, 'Major': 0.4}
    value = int(base_value * age_factor * mileage_factor * cond.get(req.condition, 1) * acc.get(req.accident_history, 1))
    value = max(150000, min(value, base_value * 1.2))
    return {
        "success": True,
        "market_value": value,
        "insurance_value": int(value * 1.1),
        "trade_in_value": int(value * 0.8),
        "forced_sale_value": int(value * 0.7),
        "certificate_number": f"AUTO-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"
    }

# ============================================
# MILEAGE ENGINE
# ============================================
@app.post("/api/mileage/calculate")
async def calculate_mileage(req: MileageRequest):
    distance = req.end_odometer - req.start_odometer
    if distance <= 0:
        raise HTTPException(400, "End odometer must be greater than start")
    rates = {'Small Hatchback': 22, 'Compact Sedan': 28, 'Midsize Sedan': 35, 'SUV/Crossover': 42, 'Large SUV': 55, 'Pickup Truck': 48, 'Minibus': 65, 'Motorcycle': 12}
    rate = rates.get(req.vehicle_category, 28)
    return {"success": True, "distance_km": distance, "rate_per_km": rate, "claim_amount": distance * rate, "currency": "KES"}

@app.get("/api/mileage/rates")
async def get_mileage_rates():
    return {"success": True, "rates": {'Small Hatchback': 22, 'Compact Sedan': 28, 'Midsize Sedan': 35, 'SUV/Crossover': 42, 'Large SUV': 55, 'Pickup Truck': 48, 'Minibus': 65, 'Motorcycle': 12}}

# ============================================
# M-PESA PRODUCTION PAYMENT
# ============================================
@app.post("/api/mpesa/stkpush")
async def mpesa_stkpush(req: MpesaRequest):
    try:
        logger.info(f"Initiating M-Pesa payment: {req.amount} KES for {req.service_type}")
        token = await get_mpesa_token()
        phone = format_phone(req.phone)
        password, timestamp = generate_mpesa_password()
        url = get_mpesa_url()
        
        body = {
            "BusinessShortCode": MPESA["SHORTCODE"],
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": req.amount,
            "PartyA": phone,
            "PartyB": MPESA["SHORTCODE"],
            "PhoneNumber": phone,
            "CallBackURL": "https://auto-v.onrender.com/api/mpesa/callback",
            "AccountReference": f"AUTOV-{int(time.time())}",
            "TransactionDesc": f"{req.service_type.upper()} Payment"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{url}/mpesa/stkpush/v1/processrequest",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body
            )
            result = r.json()
            if result.get("ResponseCode") == "0":
                logger.info(f"M-Pesa STK Push successful: {result.get('CheckoutRequestID')}")
                return {
                    "success": True,
                    "checkoutRequestID": result.get("CheckoutRequestID"),
                    "message": "Payment initiated. Check your phone for M-Pesa prompt."
                }
            logger.error(f"M-Pesa STK Push failed: {result}")
            return {"success": False, "error": result.get("errorMessage", "Payment failed")}
    except Exception as e:
        logger.error(f"M-Pesa error: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/api/mpesa/callback")
async def mpesa_callback(request: Request):
    try:
        data = await request.json()
        logger.info(f"M-Pesa Callback received")
        stk = data.get("Body", {}).get("stkCallback", {})
        result_code = stk.get("ResultCode")
        checkout_id = stk.get("CheckoutRequestID")
        
        if result_code == 0:
            metadata = {}
            for item in stk.get("CallbackMetadata", {}).get("Item", []):
                metadata[item.get("Name")] = item.get("Value")
            logger.info(f"✅ Payment successful: {metadata.get('MpesaReceiptNumber')} - {metadata.get('Amount')} KES")
        else:
            logger.error(f"❌ Payment failed: {stk.get('ResultDesc')}")
        
        return {"ResultCode": 0, "ResultDesc": "Success"}
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        return {"ResultCode": 1, "ResultDesc": str(e)}

@app.post("/api/mpesa/status")
async def mpesa_status(checkoutRequestID: str):
    return {"status": "pending", "message": "Check your phone for M-Pesa prompt"}

# ============================================
# RUN SERVER
# ============================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting AUTO-V API in PRODUCTION mode on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
