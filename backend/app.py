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
# SUPABASE CONFIGURATION (FIXED)
# ============================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tsvejnzxrxrrecgquxbq.supabase.co")
# Try SUPABASE_ANON_KEY first, fallback to SUPABASE_KEY
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
if not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_ANON_KEY or SUPABASE_KEY in environment")

logger.info(f"Supabase URL: {SUPABASE_URL}")
logger.info(f"Supabase Key: {SUPABASE_KEY[:20]}...")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# FASTAPI APP WITH LIFESPAN
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 AUTO-V API Starting...")
    logger.info(f"📡 Environment: {os.getenv('FLASK_ENV', 'production')}")
    logger.info(f"📡 Version: {os.getenv('APP_VERSION', '1.0.0')}")
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
# CORS CONFIGURATION
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://*.supabase.co",
        "https://auto-v.meipressgroup.com",
        "https://www.auto-v.meipressgroup.com",
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
# PYDANTIC MODELS
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

class MileageRateRequest(BaseModel):
    vehicle_id: str
    annual_km: int = Field(ge=0, le=200000)
    fuel_type: str = Field(..., pattern="^(petrol|diesel|hybrid|electric|lpg)$")
    journey_purpose: str = Field(..., pattern="^(business|ngo|government|private|fleet)$")
    road_condition: str = Field(..., pattern="^(highway|mixed|urban|rural|offroad)$")

# ============================================
# AUTHENTICATION DEPENDENCY
# ============================================
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token from Supabase."""
    token = credentials.credentials
    try:
        # Verify with Supabase
        user = supabase.auth.get_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ============================================
# HELPER FUNCTIONS
# ============================================
def calculate_mileage_rate(data: MileageRateRequest) -> Dict[str, Any]:
    """Calculate mileage rate based on vehicle and usage parameters."""
    # Default rates (in production, these would come from a database)
    base_rates = {
        "petrol": 18.50,
        "diesel": 16.80,
        "hybrid": 14.20,
        "electric": 8.50,
        "lpg": 12.00
    }
    
    journey_factors = {
        "business": 1.0,
        "ngo": 0.95,
        "government": 0.90,
        "private": 1.0,
        "fleet": 0.92
    }
    
    road_factors = {
        "highway": 0.85,
        "mixed": 1.0,
        "urban": 1.10,
        "rural": 0.95,
        "offroad": 1.25
    }
    
    base_rate = base_rates.get(data.fuel_type, 18.50)
    journey_factor = journey_factors.get(data.journey_purpose, 1.0)
    road_factor = road_factors.get(data.road_condition, 1.0)
    
    # Calculate rate
    rate = base_rate * journey_factor * road_factor
    
    # Annual cost
    annual_cost = rate * data.annual_km
    
    return {
        "rate_per_km": round(rate, 2),
        "annual_cost": round(annual_cost, 2),
        "base_rate": base_rate,
        "factors_applied": {
            "journey": journey_factor,
            "road": road_factor
        }
    }

# ============================================
# API ROUTES
# ============================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "success": True,
        "data": {
            "name": "AUTO-V API",
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "status": "operational",
            "docs": "/api/docs",
            "health": "/api/health"
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "environment": os.getenv("FLASK_ENV", "production"),
            "supabase_connected": supabase is not None
        }
    }

@app.get("/api/ping")
async def ping():
    """Ping endpoint."""
    return {
        "success": True,
        "data": {
            "pong": True,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

@app.post("/api/auth/register")
async def register_user(user: User):
    """Register a new user."""
    try:
        # Check if user exists
        existing = supabase.table("users").select("*").eq("email", user.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")
        
        # Create user profile
        profile_data = {
            "id": auth_response.user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("users").insert(profile_data).execute()
        
        return {
            "success": True,
            "data": {
                "user_id": auth_response.user.id,
                "email": user.email,
                "message": "User registered successfully"
            }
        }
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
async def login_user(email: str, password: str):
    """Login a user."""
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return {
            "success": True,
            "data": {
                "user_id": auth_response.user.id,
                "email": auth_response.user.email,
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token
            }
        }
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/valuation")
async def calculate_valuation(request: VehicleValuationRequest):
    """Calculate vehicle valuation."""
    try:
        # Base valuation logic
        base_value = 2000000  # Base value for new vehicle
        
        # Depreciation by year
        current_year = datetime.now().year
        age = current_year - request.year
        depreciation = age * 0.10  # 10% per year
        value = base_value * (1 - depreciation)
        
        # Condition adjustment
        condition_factors = {
            "Excellent": 1.1,
            "Good": 1.0,
            "Fair": 0.85,
            "Poor": 0.70
        }
        
        # Accident adjustment
        accident_factors = {
            "None": 1.0,
            "Minor": 0.95,
            "Moderate": 0.85,
            "Major": 0.70
        }
        
        condition_factor = condition_factors.get(request.condition, 1.0)
        accident_factor = accident_factors.get(request.accident_history, 1.0)
        
        # Odometer adjustment
        odometer_factor = max(0.5, 1 - (request.odometer / 200000))
        
        final_value = value * condition_factor * accident_factor * odometer_factor
        
        return {
            "success": True,
            "data": {
                "registration_number": request.registration_number,
                "make": request.make,
                "model": request.model,
                "year": request.year,
                "estimated_value": round(final_value, 2),
                "base_value": round(value, 2),
                "condition_adjustment": condition_factor,
                "accident_adjustment": accident_factor,
                "odometer_adjustment": round(odometer_factor, 2),
                "valuation_date": datetime.utcnow().isoformat() + "Z"
            }
        }
    except Exception as e:
        logger.error(f"Valuation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mileage/calculate")
async def calculate_mileage_rate_endpoint(request: MileageRateRequest):
    """Calculate mileage reimbursement rate."""
    try:
        result = calculate_mileage_rate(request)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Mileage calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: str):
    """Get vehicle details by ID."""
    try:
        result = supabase.table("vehicles").select("*").eq("id", vehicle_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        return {
            "success": True,
            "data": result.data[0]
        }
    except Exception as e:
        logger.error(f"Get vehicle error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/routes")
async def list_routes():
    """List all registered routes (debug)."""
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "methods": list(route.methods) if hasattr(route, 'methods') else []
        })
    return {
        "success": True,
        "data": {
            "total": len(routes),
            "routes": routes
        }
    }

# ============================================
# M-PESA ROUTES (FastAPI compatible)
# ============================================

from api.routes.mpesa import router as mpesa_router

# Register M-Pesa routes
app.include_router(mpesa_router, prefix="/api/mpesa", tags=["M-Pesa"])

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "An unexpected error occurred",
            "status_code": 500
        }
    )

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting AUTO-V on port {port}")
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        log_level="info"
    )
