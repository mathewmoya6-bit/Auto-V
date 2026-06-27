"""
AUTO-V FastAPI Application Entry Point
Supabase as Single Source of Truth
Production-ready with graceful error handling
"""

import logging
import time
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# ─── Optional Dependencies (Graceful Fallback) ──────────────
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    HAS_SLOWAPI = True
except ImportError:
    HAS_SLOWAPI = False
    Limiter = None
    get_remote_address = None
    RateLimitExceeded = None

from app.core.config import settings
from app.core.database import supabase
from app.routes import (
    health, auth, mpesa, valuation, certificates, 
    vehicles, dashboard, vin, vin_routes, webhooks, admin, 
    assessments, inspection, intelligence, payments, services, 
    valuations, fuel
)
from app.utils.logger import setup_logger, get_default_logger

# ─── Setup Logger ──────────────────────────────────────────────
logger = get_default_logger()

# ─── Rate Limiter (Optional) ──────────────────────────────────
if HAS_SLOWAPI:
    limiter = Limiter(key_func=get_remote_address)
else:
    limiter = None
    logger.warning("⚠️ slowapi not installed - rate limiting disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with graceful startup/shutdown"""
    # ─── Startup ──────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("🚀 Starting AUTO-V API (Supabase)...")
    logger.info(f"📡 Environment: {settings.ENV}")
    logger.info(f"🔗 Supabase URL: {settings.SUPABASE_URL}")
    logger.info(f"📦 Version: {settings.APP_VERSION}")
    logger.info(f"🐍 Python: {os.sys.version}")
    logger.info("=" * 60)
    
    # ─── Check Supabase Connection ──────────────────────────────
    try:
        # Test Supabase connection
        response = supabase.table("users").select("count", count="exact").limit(1).execute()
        logger.info("✅ Supabase connected successfully")
    except Exception as e:
        logger.error(f"❌ Supabase connection error: {e}")
        logger.warning("⚠️ Continuing without database...")
    
    # ─── Payment Worker ──────────────────────────────────────────
    try:
        worker = get_async_worker()
        await worker.start()
        logger.info("✅ Payment worker started")
    except Exception as e:
        logger.error(f"❌ Failed to start payment worker: {e}")
        logger.warning("⚠️ Payment worker disabled")
    
    yield
    
    # ─── Shutdown ──────────────────────────────────────────────────
    logger.info("🛑 Shutting down AUTO-V API...")
    
    # Stop payment worker
    try:
        worker = get_async_worker()
        await worker.stop()
        logger.info("✅ Payment worker stopped")
    except Exception as e:
        logger.error(f"❌ Failed to stop payment worker: {e}")


# ─── Create FastAPI App ──────────────────────────────────────────
app = FastAPI(
    title="AUTO-V API",
    version=settings.APP_VERSION,
    description="Africa's Vehicle Intelligence Platform - AI-powered valuation, inspection, fleet analytics, and verification",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "Authentication", "description": "User authentication and JWT tokens"},
        {"name": "M-Pesa", "description": "M-Pesa payment integration"},
        {"name": "Valuation", "description": "AI-powered vehicle valuation"},
        {"name": "Certificates", "description": "Certificate generation and management"},
        {"name": "Vehicles", "description": "Vehicle management"},
        {"name": "Dashboard", "description": "Dashboard analytics and statistics"},
        {"name": "VIN", "description": "VIN validation, decoding, and OCR extraction"},
        {"name": "Webhooks", "description": "Webhook endpoints for third-party integrations"},
        {"name": "Admin", "description": "Administrative endpoints for system management"},
        {"name": "Assessments", "description": "Vehicle assessment and risk evaluation"},
        {"name": "Inspections", "description": "Vehicle inspection and damage detection"},
        {"name": "Intelligence", "description": "AI-powered intelligence and analytics"},
        {"name": "Payments", "description": "Payment processing and management"},
        {"name": "Services", "description": "Service request management"},
        {"name": "Fuel", "description": "EPRA fuel price management"}
    ]
)

# ─── Rate Limit Handler (Optional) ──────────────────────────────
if HAS_SLOWAPI:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, lambda req, exc: JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "Rate limit exceeded",
            "message": str(exc)
        }
    ))
else:
    # Fallback rate limit handler (no-op)
    app.add_exception_handler(Exception, lambda req, exc: JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"}
    ))


# ─── CORS Middleware ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

# ─── Trusted Host Middleware ──────────────────────────────────────
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.CORS_ORIGINS + ["localhost", "127.0.0.1"]
)


# ─── Request ID Middleware ──────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to each request"""
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        import uuid
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ─── Root and Health Endpoints ──────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "name": "AUTO-V API",
        "version": settings.APP_VERSION,
        "description": "Africa's Vehicle Intelligence Platform",
        "docs": "/docs",
        "status": "operational"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint with Supabase status"""
    supabase_status = "unknown"
    try:
        response = supabase.table("users").select("count", count="exact").limit(1).execute()
        supabase_status = "connected"
    except Exception as e:
        supabase_status = f"disconnected: {str(e)[:50]}..."
    
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "timestamp": time.time(),
        "supabase": supabase_status,
        "rate_limiting": "enabled" if HAS_SLOWAPI else "disabled"
    }


# ─── Include All Routers ──────────────────────────────────────

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(mpesa.router)
app.include_router(valuation.router)
app.include_router(valuations.router)
app.include_router(certificates.router)
app.include_router(vehicles.router)
app.include_router(dashboard.router)
app.include_router(vin.router)
app.include_router(vin_routes.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
app.include_router(assessments.router)
app.include_router(inspection.router)
app.include_router(intelligence.router)
app.include_router(payments.router)
app.include_router(services.router)
app.include_router(fuel.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
