# backend/main.py - Fixed version
import os
import logging
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
from typing import Optional, Dict, Any
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="AUTO-V API",
    description="Vehicle Valuation, Inspection & AI Services",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tsvejnzxrxrrecgquxbq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Security - HTTP Bearer token
security = HTTPBearer()

# ============================================
# DEPENDENCIES
# ============================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from Bearer token"""
    token = credentials.credentials
    try:
        user = supabase.auth.get_user(token)
        return user.user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# ============================================
# HEALTH ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {
        "name": "AUTO-V API",
        "version": "2.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "supabase": "connected",
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# VALUATION ENDPOINT
# ============================================

@app.post("/api/valuation/calculate")
async def calculate_valuation(data: Dict[str, Any], user = Depends(get_current_user)):
    """Calculate vehicle valuation"""
    try:
        make = data.get("make", "")
        year = data.get("year", 2020)
        mileage = data.get("mileage", 0)
        condition = data.get("condition", 8)
        
        # Simple valuation calculation
        current_year = datetime.now().year
        age = current_year - year
        base_value = 2000000
        depreciation = min(age * 0.08, 0.70)
        market_value = base_value * (1 - depreciation)
        
        # Brand adjustments
        if make.lower() == "toyota":
            market_value *= 1.15
        elif make.lower() == "mercedes":
            market_value *= 1.25
        
        # Mileage adjustment
        mileage_factor = max(0.45, 1 - (mileage / 300000))
        market_value *= mileage_factor
        
        # Condition adjustment
        condition_factor = condition / 10
        market_value *= condition_factor
        
        market_value = max(150000, round(market_value / 1000) * 1000)
        
        return {
            "success": True,
            "result": {
                "market_value": market_value,
                "insurance_value": round(market_value * 1.1),
                "trade_in_value": round(market_value * 0.8),
                "forced_sale_value": round(market_value * 0.7),
                "depreciation_rate": int(depreciation * 100),
                "age_years": age
            }
        }
    except Exception as e:
        logger.error(f"Valuation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# SERVICE REQUEST ENDPOINTS
# ============================================

@app.post("/api/requests/create")
async def create_service_request(data: Dict[str, Any], user = Depends(get_current_user)):
    """Create a new service request"""
    try:
        service_data = {
            "user_id": user.id,
            "service_type": data.get("service_type"),
            "registration_number": data.get("registration_number"),
            "make": data.get("make"),
            "model": data.get("model"),
            "year": data.get("year"),
            "amount": data.get("amount"),
            "phone": data.get("phone"),
            "payment_status": "pending",
            "status": "awaiting_payment",
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.table("service_requests").insert(service_data).execute()
        return {"success": True, "request_id": result.data[0]["id"]}
    except Exception as e:
        logger.error(f"Create request error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/requests/{user_id}")
async def get_user_requests(user_id: str):
    """Get all service requests for a user"""
    try:
        result = supabase.table("service_requests")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        return {"success": True, "requests": result.data}
    except Exception as e:
        logger.error(f"Get requests error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# RUN APPLICATION
# ============================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
