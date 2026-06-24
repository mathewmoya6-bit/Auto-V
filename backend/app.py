"""
AUTO-V Backend API
FastAPI + Supabase Integration
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ─── Logging ──────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Supabase Configuration ──────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")

logger.info(f"✅ Supabase URL: {SUPABASE_URL}")
logger.info(f"✅ Supabase Key: {SUPABASE_ANON_KEY[:20]}...")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ─── FastAPI App ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AUTO-V API Starting...")
    yield
    logger.info("👋 AUTO-V API Shutting down...")

app = FastAPI(
    title="AUTO-V API",
    description="Vehicle Valuation, Inspection, and Mileage Reimbursement API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# ─── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://auto-v.meipressgroup.com",
        "https://www.auto-v.meipressgroup.com",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

security = HTTPBearer()

# ─── Models ──────────────────────────────────────────────────
class VehicleValuationRequest(BaseModel):
    registration_number: str = Field(..., min_length=3, max_length=20)
    make: str = Field(..., min_length=2)
    model: str = Field(..., min_length=1)
    year: int = Field(ge=1950, le=datetime.now().year)
    odometer: int = Field(ge=0, le=500000)
    condition: str = Field(..., pattern="^(Excellent|Good|Fair|Poor)$")
    accident_history: str = Field(..., pattern="^(None|Minor|Moderate|Major)$")
    valuation_purpose: str

# ─── Routes ──────────────────────────────────────────────────

@app.get("/")
async def root():
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
    return {"success": True, "data": {"pong": True, "timestamp": datetime.utcnow().isoformat() + "Z"}}

@app.get("/api/routes")
async def list_routes():
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "methods": list(route.methods) if hasattr(route, 'methods') else []
        })
    return {"success": True, "data": {"total": len(routes), "routes": routes}}

# ─── Import and Register M-Pesa Routes ──────────────────────
from api.routes.mpesa import router as mpesa_router
app.include_router(mpesa_router, prefix="/api/mpesa", tags=["M-Pesa"])

# ─── Error Handlers ──────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "An unexpected error occurred", "status_code": 500}
    )

# ─── Main Entry ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        log_level="info"
    )
