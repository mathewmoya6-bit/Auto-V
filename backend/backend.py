"""
AUTO-V Backend API
FastAPI + Supabase Integration
Updated with better error handling, CORS, and async support
"""

from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import os
import uuid
import logging
from supabase import create_client, Client
from dotenv import load_dotenv
import httpx
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# SUPABASE CONFIGURATION
# ============================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tsvejnzxrxrrecgquxbq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-supabase-anon-key")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# FASTAPI APP WITH LIFESPAN
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 AUTO-V API Starting...")
    yield
    # Shutdown
    logger.info("👋 AUTO-V API Shutting down...")

app = FastAPI(
    title="AUTO-V API",
    description="Vehicle Valuation, Inspection, and Mileage Reimbursement API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# ============================================
# CORS CONFIGURATION (Updated)
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://*.supabase.co",
        "*"  # For development - restrict in production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Security
security = HTTPBearer()

# ============================================
# PYDANTIC MODELS (Updated with validators)
# ============================================

class User(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: Optional[str] = Field(None, min_length=6)
    full_name: Optional[str] = None
    phone: Optional[str] = Field(None, pattern=r'^[0-9]{10,12}$')

class VehicleValuationRequest(BaseModel):
    registration_number: str = Field(..., min_length=3, max_length=20)
    make: str = Field(..., min_length=2)
    model: str = Field(..., min_length=1)
    year: int = Field(ge=1950, le=datetime.now().year)
    odometer: int = Field(ge=0, le=500000)
    condition: str = Field(..., pattern="^(Excellent|Good|Fair|Poor)$")
    accident_history: str = Field(..., pattern="^(None|Minor|Moderate|Major)$")
    valuation_purpose: str
    
    @validator('registration_number')
    def validate_registration(cls, v):
        v = v.upper().strip()
        return v

class ValuationResult(BaseModel):
    market_value: int
    insurance_value: int
    trade_in_value: int
    forced_sale_value: int
    certificate_number: str
    valuation_date: datetime
    estimated_monthly_payment: Optional[int] = None

class MileageClaimRequest(BaseModel):
    trip_date: date
    start_location: str
    end_location: str
    purpose: str
    start_odometer: int = Field(ge=0)
    end_odometer: int = Field(ge=0)
    vehicle_category: str
    notes: Optional[str] = None
    
    @validator('end_odometer')
    def validate_odometer(cls, v, values):
        if 'start_odometer' in values and v <= values['start_odometer']:
            raise ValueError('End odometer must be greater than start odometer')
        return v

class MileageClaimResponse(BaseModel):
    id: str
    distance_km: int
    rate_per_km: float
    claim_amount: float
    status: str
    created_at: datetime

class InspectionRequest(BaseModel):
    vehicle_id: str
    engine_score: int = Field(ge=0, le=10)
    transmission_score: int = Field(ge=0, le=10)
    body_score: int = Field(ge=0, le=10)
    interior_score: int = Field(ge=0, le=10)
    electrical_score: int = Field(ge=0, le=10)
    tires_score: int = Field(ge=0, le=10)
    photos: Optional[List[str]] = None
    notes: Optional[str] = None

class FuelPriceUpdate(BaseModel):
    fuel_type: str = Field(..., pattern="^(petrol|diesel|kerosene)$")
    price_per_litre: float = Field(ge=0)
    region: str = "National"
    effective_date: date

# ============================================
# HELPER FUNCTIONS
# ============================================

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and get current user"""
    try:
        # Verify token with Supabase
        user = supabase.auth.get_user(token.credentials)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))

def calculate_vehicle_valuation(data: VehicleValuationRequest) -> ValuationResult:
    """Calculate vehicle valuation based on inputs"""
    # Base values by make (2024 updated)
    base_values = {
        'toyota': 3200000,
        'mercedes': 5500000,
        'bmw': 4800000,
        'honda': 2800000,
        'nissan': 2600000,
        'mazda': 2500000,
        'subaru': 2900000,
        'volkswagen': 2700000,
        'hyundai': 2300000,
        'ford': 2400000,
        'suzuki': 1800000,
        'mitsubishi': 2500000
    }
    
    default_base = 2200000
    base_value = base_values.get(data.make.lower(), default_base)
    
    # Calculate factors
    current_year = datetime.now().year
    age = current_year - data.year
    age_factor = max(0.30, 1 - (age * 0.07))
    mileage_factor = max(0.40, 1 - (data.odometer / 350000))
    
    condition_factors = {
        'Excellent': 1.20,
        'Good': 1.0, 
        'Fair': 0.85,
        'Poor': 0.65
    }
    condition_factor = condition_factors.get(data.condition, 1.0)
    
    accident_factors = {
        'None': 1.0,
        'Minor': 0.85,
        'Moderate': 0.60,
        'Major': 0.35
    }
    accident_factor = accident_factors.get(data.accident_history, 1.0)
    
    # Calculate market value
    market_value = int(base_value * age_factor * mileage_factor * condition_factor * accident_factor)
    market_value = max(150000, min(market_value, base_value * 1.3))
    
    # Generate certificate number
    timestamp = int(datetime.now().timestamp())
    cert_id = uuid.uuid4().hex[:8].upper()
    certificate_number = f"AUTO-V-{timestamp}-{cert_id}"
    
    # Calculate estimated monthly payment (for loan purposes)
    estimated_monthly_payment = int(market_value * 0.025) if data.valuation_purpose == "Loan / Security" else None
    
    return ValuationResult(
        market_value=market_value,
        insurance_value=int(market_value * 1.12),
        trade_in_value=int(market_value * 0.75),
        forced_sale_value=int(market_value * 0.65),
        certificate_number=certificate_number,
        valuation_date=datetime.now(),
        estimated_monthly_payment=estimated_monthly_payment
    )

async def get_mileage_rate(category: str) -> float:
    """Get mileage rate from Supabase with fallback"""
    rates = {
        'Small Hatchback': 22.0,
        'Compact Sedan': 28.0,
        'Midsize Sedan': 35.0,
        'SUV/Crossover': 42.0,
        'Large SUV': 55.0,
        'Pickup Truck': 48.0,
        'Minibus': 65.0,
        'Motorcycle': 12.0,
        'Three-Wheeler': 15.0
    }
    
    # Try to get from database first
    try:
        response = supabase.table("mileage_rates") \
            .select("rate_per_km") \
            .eq("vehicle_category", category) \
            .eq("is_active", True) \
            .execute()
        
        if response.data and len(response.data) > 0:
            return float(response.data[0]['rate_per_km'])
    except Exception as e:
        logger.warning(f"Could not fetch rate from DB: {e}")
    
    return rates.get(category, 25.0)

# ============================================
# HEALTH & ROOT ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {
        "message": "AUTO-V API",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "docs": "/api/docs",
            "valuation": "/api/valuation",
            "mileage": "/api/mileage",
            "inspection": "/api/inspection"
        }
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "supabase_connected": True
    }

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.post("/api/auth/register")
async def register_user(user: User):
    """Register a new user"""
    try:
        if not user.password:
            raise HTTPException(status_code=400, detail="Password required")
            
        response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        
        # Store additional user info
        if response.user:
            supabase.table("user_profiles").insert({
                "id": response.user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone
            }).execute()
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user": {
                "id": response.user.id,
                "email": response.user.email
            }
        }
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/login")
async def login_user(user: User):
    """Login user"""
    try:
        if not user.password:
            raise HTTPException(status_code=400, detail="Password required")
            
        response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })
        
        return {
            "success": True,
            "message": "Login successful",
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": {
                "id": response.user.id,
                "email": response.user.email
            }
        }
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/auth/logout")
async def logout_user(user=Depends(get_current_user)):
    """Logout user"""
    try:
        supabase.auth.sign_out()
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# VALUATION ENDPOINTS
# ============================================

@app.post("/api/valuation/calculate", response_model=ValuationResult)
async def calculate_valuation(data: VehicleValuationRequest, user=Depends(get_current_user)):
    """Calculate vehicle valuation"""
    try:
        result = calculate_vehicle_valuation(data)
        
        # Save to database
        supabase.table("service_requests").insert({
            "user_id": user.user.id,
            "service_type": "valuation",
            "registration_number": data.registration_number,
            "make": data.make,
            "model": data.model,
            "year": data.year,
            "odometer": data.odometer,
            "condition": data.condition,
            "accident_history": data.accident_history,
            "valuation_purpose": data.valuation_purpose,
            "result": result.dict(),
            "status": "completed",
            "payment_status": "paid",
            "created_at": datetime.now().isoformat()
        }).execute()
        
        logger.info(f"Valuation completed for user {user.user.id}")
        return result
        
    except Exception as e:
        logger.error(f"Valuation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/valuation/history")
async def get_valuation_history(user=Depends(get_current_user)):
    """Get user's valuation history"""
    try:
        response = supabase.table("service_requests") \
            .select("*") \
            .eq("user_id", user.user.id) \
            .eq("service_type", "valuation") \
            .order("created_at", desc=True) \
            .execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        logger.error(f"History error: {str(e)}")
        return {"success": True, "data": []}

@app.get("/api/valuation/certificate/{certificate_number}")
async def get_certificate(certificate_number: str):
    """Get valuation certificate by number"""
    try:
        response = supabase.table("service_requests") \
            .select("*") \
            .eq("result->>certificate_number", certificate_number) \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Certificate not found")
        
        return {"success": True, "data": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# MILEAGE CLAIM ENDPOINTS
# ============================================

@app.post("/api/mileage/claim", response_model=MileageClaimResponse)
async def submit_mileage_claim(data: MileageClaimRequest, user=Depends(get_current_user)):
    """Submit a mileage claim"""
    try:
        # Calculate distance and amount
        distance_km = data.end_odometer - data.start_odometer
        
        rate_per_km = await get_mileage_rate(data.vehicle_category)
        claim_amount = distance_km * rate_per_km
        
        claim_id = str(uuid.uuid4())
        
        # Save to database
        response = supabase.table("mileage_claims").insert({
            "id": claim_id,
            "user_id": user.user.id,
            "employee_name": user.user.email.split('@')[0],
            "trip_date": data.trip_date.isoformat(),
            "start_location": data.start_location,
            "end_location": data.end_location,
            "purpose": data.purpose,
            "start_odometer": data.start_odometer,
            "end_odometer": data.end_odometer,
            "distance_km": distance_km,
            "rate_per_km": rate_per_km,
            "claim_amount": claim_amount,
            "notes": data.notes,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }).execute()
        
        logger.info(f"Mileage claim submitted for user {user.user.id}: {claim_amount} KES")
        
        return MileageClaimResponse(
            id=claim_id,
            distance_km=distance_km,
            rate_per_km=rate_per_km,
            claim_amount=claim_amount,
            status="pending",
            created_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Claim submission error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mileage/claims")
async def get_mileage_claims(user=Depends(get_current_user)):
    """Get user's mileage claims"""
    try:
        response = supabase.table("mileage_claims") \
            .select("*") \
            .eq("user_id", user.user.id) \
            .order("trip_date", desc=True) \
            .execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        logger.error(f"Get claims error: {str(e)}")
        return {"success": True, "data": []}

@app.get("/api/mileage/claims/{claim_id}")
async def get_mileage_claim(claim_id: str, user=Depends(get_current_user)):
    """Get a specific mileage claim"""
    try:
        response = supabase.table("mileage_claims") \
            .select("*") \
            .eq("id", claim_id) \
            .eq("user_id", user.user.id) \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        return {"success": True, "data": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/mileage/claims/{claim_id}")
async def cancel_mileage_claim(claim_id: str, user=Depends(get_current_user)):
    """Cancel a pending mileage claim"""
    try:
        # First check if claim exists and is pending
        response = supabase.table("mileage_claims") \
            .select("*") \
            .eq("id", claim_id) \
            .eq("user_id", user.user.id) \
            .eq("status", "pending") \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Claim not found or cannot be cancelled")
        
        # Delete the claim
        supabase.table("mileage_claims") \
            .delete() \
            .eq("id", claim_id) \
            .execute()
        
        logger.info(f"Mileage claim {claim_id} cancelled by user {user.user.id}")
        return {"success": True, "message": "Claim cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mileage/rates")
async def get_mileage_rates():
    """Get current mileage rates"""
    try:
        response = supabase.table("mileage_rates") \
            .select("*") \
            .eq("is_active", True) \
            .order("rate_per_km") \
            .execute()
        
        if response.data:
            return {"success": True, "data": response.data}
        
        # Return default rates
        default_rates = [
            {"vehicle_category": "Small Hatchback", "rate_per_km": 22.0},
            {"vehicle_category": "Compact Sedan", "rate_per_km": 28.0},
            {"vehicle_category": "Midsize Sedan", "rate_per_km": 35.0},
            {"vehicle_category": "SUV/Crossover", "rate_per_km": 42.0},
            {"vehicle_category": "Large SUV", "rate_per_km": 55.0},
            {"vehicle_category": "Pickup Truck", "rate_per_km": 48.0},
            {"vehicle_category": "Minibus", "rate_per_km": 65.0},
            {"vehicle_category": "Motorcycle", "rate_per_km": 12.0},
            {"vehicle_category": "Three-Wheeler", "rate_per_km": 15.0}
        ]
        return {"success": True, "data": default_rates, "source": "default"}
        
    except Exception as e:
        logger.error(f"Get rates error: {str(e)}")
        return {"success": True, "data": []}

# ============================================
# INSPECTION ENDPOINTS
# ============================================

@app.post("/api/inspection/submit")
async def submit_inspection(data: InspectionRequest, user=Depends(get_current_user)):
    """Submit vehicle inspection results"""
    try:
        # Calculate overall score
        scores = [
            data.engine_score,
            data.transmission_score,
            data.body_score,
            data.interior_score,
            data.electrical_score,
            data.tires_score
        ]
        overall_score = sum(scores) / len(scores)
        
        # Determine rating
        if overall_score >= 8.5:
            rating = "Excellent"
        elif overall_score >= 7.0:
            rating = "Good"
        elif overall_score >= 5.0:
            rating = "Fair"
        else:
            rating = "Poor"
        
        certificate_number = f"INS-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:6].upper()}"
        
        inspection_result = {
            "engine_score": data.engine_score,
            "transmission_score": data.transmission_score,
            "body_score": data.body_score,
            "interior_score": data.interior_score,
            "electrical_score": data.electrical_score,
            "tires_score": data.tires_score,
            "overall_score": round(overall_score, 1),
            "rating": rating,
            "certificate_number": certificate_number,
            "inspection_date": datetime.now().isoformat(),
            "notes": data.notes
        }
        
        # Save to database
        supabase.table("service_requests").insert({
            "user_id": user.user.id,
            "service_type": "inspection",
            "vehicle_id": data.vehicle_id,
            "result": inspection_result,
            "status": "completed",
            "payment_status": "paid",
            "created_at": datetime.now().isoformat()
        }).execute()
        
        logger.info(f"Inspection completed for user {user.user.id}, score: {overall_score}")
        
        return {
            "success": True,
            "data": inspection_result
        }
        
    except Exception as e:
        logger.error(f"Inspection error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# DASHBOARD & STATS ENDPOINTS
# ============================================

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(user=Depends(get_current_user)):
    """Get user dashboard statistics"""
    try:
        # Get valuations
        valuations = supabase.table("service_requests") \
            .select("*") \
            .eq("user_id", user.user.id) \
            .eq("service_type", "valuation") \
            .execute()
        
        # Get inspections
        inspections = supabase.table("service_requests") \
            .select("*") \
            .eq("user_id", user.user.id) \
            .eq("service_type", "inspection") \
            .execute()
        
        # Get mileage claims
        claims = supabase.table("mileage_claims") \
            .select("*") \
            .eq("user_id", user.user.id) \
            .execute()
        
        total_claimed = sum(c.get('claim_amount', 0) for c in claims.data) if claims.data else 0
        pending_claims = sum(1 for c in claims.data if c.get('status') == 'pending') if claims.data else 0
        
        return {
            "success": True,
            "data": {
                "total_valuations": len(valuations.data) if valuations.data else 0,
                "total_inspections": len(inspections.data) if inspections.data else 0,
                "total_mileage_claims": len(claims.data) if claims.data else 0,
                "total_reimbursed": total_claimed,
                "pending_claims": pending_claims,
                "recent_valuations": valuations.data[:3] if valuations.data else [],
                "recent_claims": claims.data[:3] if claims.data else []
            }
        }
        
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return {"success": True, "data": {}}

# ============================================
# FUEL PRICE ENDPOINTS
# ============================================

@app.post("/api/fuel/prices")
async def add_fuel_price(data: FuelPriceUpdate, user=Depends(get_current_user)):
    """Add or update fuel price"""
    try:
        # Check if admin (you can implement admin check)
        response = supabase.table("fuel_prices").insert({
            "fuel_type": data.fuel_type,
            "price_per_litre": data.price_per_litre,
            "region": data.region,
            "effective_date": data.effective_date.isoformat(),
            "created_at": datetime.now().isoformat()
        }).execute()
        
        logger.info(f"Fuel price updated: {data.fuel_type} @ {data.price_per_litre} KES")
        
        return {"success": True, "message": "Fuel price updated successfully"}
        
    except Exception as e:
        logger.error(f"Fuel price error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fuel/prices")
async def get_fuel_prices(region: str = "National"):
    """Get current fuel prices"""
    try:
        response = supabase.table("fuel_prices") \
            .select("*") \
            .eq("region", region) \
            .order("effective_date", desc=True) \
            .execute()
        
        return {"success": True, "data": response.data}
        
    except Exception as e:
        logger.error(f"Get fuel prices error: {str(e)}")
        return {"success": True, "data": []}

# ============================================
# RUN SERVER
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
