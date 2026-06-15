"""
AUTO-V Backend API
FastAPI + Supabase Integration
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="AUTO-V API",
    description="Vehicle Valuation, Inspection, and Mileage Reimbursement API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tsvejnzxrxrrecgquxbq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-supabase-anon-key")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Security
security = HTTPBearer()

# ============================================
# PYDANTIC MODELS
# ============================================

class User(BaseModel):
    email: str
    password: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None

class VehicleValuationRequest(BaseModel):
    registration_number: str
    make: str
    model: str
    year: int = Field(ge=1950, le=datetime.now().year)
    odometer: int = Field(ge=0)
    condition: str = Field(..., pattern="^(Excellent|Good|Fair|Poor)$")
    accident_history: str = Field(..., pattern="^(None|Minor|Moderate|Major)$")
    valuation_purpose: str

class ValuationResult(BaseModel):
    market_value: int
    insurance_value: int
    trade_in_value: int
    forced_sale_value: int
    certificate_number: str
    valuation_date: datetime

class MileageClaimRequest(BaseModel):
    trip_date: date
    start_location: str
    end_location: str
    purpose: str
    start_odometer: int
    end_odometer: int
    vehicle_category: str
    notes: Optional[str] = None

class MileageClaimResponse(BaseModel):
    id: str
    distance_km: int
    rate_per_km: float
    claim_amount: float
    status: str

class InspectionRequest(BaseModel):
    vehicle_id: str
    engine_score: int = Field(ge=0, le=10)
    transmission_score: int = Field(ge=0, le=10)
    body_score: int = Field(ge=0, le=10)
    interior_score: int = Field(ge=0, le=10)
    electrical_score: int = Field(ge=0, le=10)
    tires_score: int = Field(ge=0, le=10)
    notes: Optional[str] = None

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and get current user"""
    try:
        # Verify token with Supabase
        user = supabase.auth.get_user(token.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

def calculate_vehicle_valuation(data: VehicleValuationRequest) -> ValuationResult:
    """Calculate vehicle valuation based on inputs"""
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
    
    default_base = 2000000
    base_value = base_values.get(data.make.lower(), default_base)
    
    # Calculate factors
    current_year = datetime.now().year
    age = current_year - data.year
    age_factor = max(0.35, 1 - (age * 0.08))
    mileage_factor = max(0.45, 1 - (data.odometer / 300000))
    
    condition_factors = {'Excellent': 1.15, 'Good': 1.0, 'Fair': 0.85, 'Poor': 0.7}
    condition_factor = condition_factors.get(data.condition, 1.0)
    
    accident_factors = {'None': 1.0, 'Minor': 0.85, 'Moderate': 0.65, 'Major': 0.4}
    accident_factor = accident_factors.get(data.accident_history, 1.0)
    
    # Calculate market value
    market_value = int(base_value * age_factor * mileage_factor * condition_factor * accident_factor)
    market_value = max(150000, min(market_value, base_value * 1.2))
    
    # Generate certificate number
    certificate_number = f"AUTO-{int(datetime.now().timestamp())}-{os.urandom(4).hex().upper()}"
    
    return ValuationResult(
        market_value=market_value,
        insurance_value=int(market_value * 1.1),
        trade_in_value=int(market_value * 0.8),
        forced_sale_value=int(market_value * 0.7),
        certificate_number=certificate_number,
        valuation_date=datetime.now()
    )

def get_mileage_rate(category: str) -> float:
    """Get mileage rate from Supabase"""
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
    return rates.get(category, 25.0)

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {
        "message": "AUTO-V API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "docs": "/api/docs",
            "valuation": "/api/valuation",
            "mileage": "/api/mileage",
            "inspection": "/api/inspection"
        }
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.post("/api/auth/register")
async def register_user(user: User):
    """Register a new user"""
    try:
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
        
        return {"message": "User registered successfully", "user": response.user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/login")
async def login_user(user: User):
    """Login user"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })
        return {
            "message": "Login successful",
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": response.user
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

# ============================================
# VALUATION ENDPOINTS
# ============================================

@app.post("/api/valuation/calculate", response_model=ValuationResult)
async def calculate_valuation(data: VehicleValuationRequest, user=Depends(get_current_user)):
    """Calculate vehicle valuation"""
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
        "payment_status": "paid"
    }).execute()
    
    return result

@app.get("/api/valuation/history")
async def get_valuation_history(user=Depends(get_current_user)):
    """Get user's valuation history"""
    response = supabase.table("service_requests") \
        .select("*") \
        .eq("user_id", user.user.id) \
        .eq("service_type", "valuation") \
        .order("created_at", desc=True) \
        .execute()
    return response.data

# ============================================
# MILEAGE CLAIM ENDPOINTS
# ============================================

@app.post("/api/mileage/claim", response_model=MileageClaimResponse)
async def submit_mileage_claim(data: MileageClaimRequest, user=Depends(get_current_user)):
    """Submit a mileage claim"""
    # Calculate distance and amount
    distance_km = data.end_odometer - data.start_odometer
    if distance_km <= 0:
        raise HTTPException(status_code=400, detail="End odometer must be greater than start odometer")
    
    rate_per_km = get_mileage_rate(data.vehicle_category)
    claim_amount = distance_km * rate_per_km
    
    # Save to database
    response = supabase.table("mileage_claims").insert({
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
        "status": "pending"
    }).execute()
    
    claim = response.data[0]
    return MileageClaimResponse(
        id=claim['id'],
        distance_km=distance_km,
        rate_per_km=rate_per_km,
        claim_amount=claim_amount,
        status="pending"
    )

@app.get("/api/mileage/claims")
async def get_mileage_claims(user=Depends(get_current_user)):
    """Get user's mileage claims"""
    response = supabase.table("mileage_claims") \
        .select("*") \
        .eq("user_id", user.user.id) \
        .order("trip_date", desc=True) \
        .execute()
    return response.data

@app.get("/api/mileage/rates")
async def get_mileage_rates():
    """Get current mileage rates"""
    response = supabase.table("mileage_rates") \
        .select("*") \
        .eq("is_active", True) \
        .execute()
    
    if not response.data:
        # Return default rates if none in DB
        return [
            {"vehicle_category": "Small Hatchback", "rate_per_km": 22.0},
            {"vehicle_category": "Compact Sedan", "rate_per_km": 28.0},
            {"vehicle_category": "Midsize Sedan", "rate_per_km": 35.0},
            {"vehicle_category": "SUV/Crossover", "rate_per_km": 42.0},
            {"vehicle_category": "Large SUV", "rate_per_km": 55.0},
            {"vehicle_category": "Pickup Truck", "rate_per_km": 48.0},
            {"vehicle_category": "Minibus", "rate_per_km": 65.0},
            {"vehicle_category": "Motorcycle", "rate_per_km": 12.0}
        ]
    return response.data

# ============================================
# INSPECTION ENDPOINTS
# ============================================

@app.post("/api/inspection/submit")
async def submit_inspection(data: InspectionRequest, user=Depends(get_current_user)):
    """Submit vehicle inspection results"""
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
    
    inspection_result = {
        "engine_score": data.engine_score,
        "transmission_score": data.transmission_score,
        "body_score": data.body_score,
        "interior_score": data.interior_score,
        "electrical_score": data.electrical_score,
        "tires_score": data.tires_score,
        "overall_score": round(overall_score, 1),
        "certificate_number": f"INS-{int(datetime.now().timestamp())}-{os.urandom(4).hex().upper()}",
        "inspection_date": datetime.now().isoformat()
    }
    
    # Save to database
    response = supabase.table("service_requests").insert({
        "user_id": user.user.id,
        "service_type": "inspection",
        "vehicle_id": data.vehicle_id,
        "result": inspection_result,
        "status": "completed",
        "payment_status": "paid"
    }).execute()
    
    return inspection_result

# ============================================
# DASHBOARD ENDPOINTS
# ============================================

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(user=Depends(get_current_user)):
    """Get user dashboard statistics"""
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
    
    return {
        "total_valuations": len(valuations.data) if valuations.data else 0,
        "total_inspections": len(inspections.data) if inspections.data else 0,
        "total_mileage_claims": len(claims.data) if claims.data else 0,
        "total_reimbursed": total_claimed,
        "recent_activity": {
            "recent_valuations": valuations.data[:5] if valuations.data else [],
            "recent_claims": claims.data[:5] if claims.data else []
        }
    }

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
