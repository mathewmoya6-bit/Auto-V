"""
AUTO-V FastAPI Application Entry Point
Complete with all routes, middleware, and configuration
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
from app.core.database import db
from app.routes import (
    health, auth, mpesa, valuation, certificates, 
    vehicles, dashboard, vin, vin_routes, webhooks, admin, 
    assessments, inspection, intelligence, payments, services, 
    valuations, fuel
)
from app.workers import get_async_worker
from app.utils.logger import setup_logger, get_default_logger

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
    logger.info(f"🔗 Database: {settings.MONGODB_URI}")
    logger.info(f"📦 Version: {settings.APP_VERSION}")
    
    # Connect to database
    try:
        await db.connect()
        logger.info("✅ Database connected successfully")
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
    
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
    
    # Disconnect database
    try:
        await db.disconnect()
        logger.info("✅ Database disconnected")
    except Exception as e:
        logger.error(f"❌ Database disconnection error: {e}")
    
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
        {"name": "Admin", "description": "Administrative endpoints for system management"},
        {"name": "Assessments", "description": "Vehicle assessment and risk evaluation"},
        {"name": "Inspections", "description": "Vehicle inspection and damage detection"},
        {"name": "Intelligence", "description": "AI-powered intelligence and analytics"},
        {"name": "Payments", "description": "Payment processing and management"},
        {"name": "Services", "description": "Service request management"},
        {"name": "Fuel", "description": "EPRA fuel price management"}
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
    allowed_hosts=settings.CORS_ORIGINS + ["localhost", "127.0.0.1"]
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


# ─── Root and Health Endpoints ──────────────────────────────

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
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "timestamp": time.time(),
        "database": "connected" if db.is_connected else "disconnected"
    }


# ─── Include All Routers ──────────────────────────────────────

# Health
app.include_router(health.router)

# Authentication
app.include_router(auth.router)

# M-Pesa
app.include_router(mpesa.router)

# Valuation
app.include_router(valuation.router)
app.include_router(valuations.router)

# Certificates
app.include_router(certificates.router)

# Vehicles
app.include_router(vehicles.router)

# Dashboard
app.include_router(dashboard.router)

# VIN
app.include_router(vin.router)
app.include_router(vin_routes.router)

# Webhooks
app.include_router(webhooks.router)

# Admin
app.include_router(admin.router)

# Assessments
app.include_router(assessments.router)

# Inspections
app.include_router(inspection.router)

# Intelligence
app.include_router(intelligence.router)

# Payments
app.include_router(payments.router)

# Services
app.include_router(services.router)

# Fuel
app.include_router(fuel.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
