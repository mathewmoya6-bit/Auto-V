"""
AUTO-V FastAPI Application Entry Point
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import force_supabase_connection, check_supabase_health
from app.routes import (
    health, auth, mpesa, valuation, certificates, 
    vehicles, dashboard, vin, webhooks, admin
)
from app.workers import get_async_worker
from app.utils.logger import get_default_logger

# Setup logger
logger = get_default_logger()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting AUTO-V API...")
    logger.info(f"📡 Environment: {settings.ENV}")
    logger.info(f"🔗 Database: {settings.SUPABASE_URL}")
    logger.info(f"📦 Version: {settings.APP_VERSION}")
    
    # Test Supabase connection
    try:
        connected = force_supabase_connection()
        if connected:
            logger.info("✅ Supabase connected successfully")
        else:
            logger.warning("⚠️ Supabase connection failed on startup")
    except Exception as e:
        logger.error(f"❌ Supabase connection error: {e}")
    
    # Start payment worker
    try:
        worker = get_async_worker()
        await worker.start()
        logger.info("✅ Payment worker started")
    except Exception as e:
        logger.error(f"❌ Failed to start payment worker: {e}")
    
    yield
    # Shutdown
    logger.info("🛑 Shutting down AUTO-V API...")
    
    # Stop payment worker
    try:
        worker = get_async_worker()
        await worker.stop()
        logger.info("✅ Payment worker stopped")
    except Exception as e:
        logger.error(f"❌ Failed to stop payment worker: {e}")


# Create FastAPI app
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
        {"name": "Admin", "description": "Administrative endpoints for system management"}
    ]
)

# Rate limit handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda req, exc: JSONResponse(
    status_code=429,
    content={
        "success": False,
        "error": "Rate limit exceeded",
        "message": str(exc)
    }
))

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Request ID middleware
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

# Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and responses"""
    start_time = time.time()
    logger.info(f"📥 {request.method} {request.url.path}")
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"📤 {response.status_code} {request.method} {request.url.path} - {duration:.3f}s")
    return response


# ─── Root and Health Endpoints ──────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
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
    supabase_health = check_supabase_health()
    
    status = "healthy" if supabase_health.get("connected") else "degraded"
    logger.info(f"Health check: {status}")
    
    return {
        "status": status,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "timestamp": time.time(),
        "supabase": supabase_health
    }


# ─── Include Routers ──────────────────────────────────────

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(mpesa.router)
app.include_router(valuation.router)
app.include_router(certificates.router)
app.include_router(vehicles.router)
app.include_router(dashboard.router)
app.include_router(vin.router)
app.include_router(webhooks.router)
app.include_router(admin.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
