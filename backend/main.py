# app/main.py - FastAPI Application Entry Point
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_db, close_db
from app.api.v1.routes import auth, vehicles, payments, valuations, webhooks, users, reports, certificates, mileage, fleet, admin
from app.middleware.rate_limit import RateLimitMiddleware

# Setup logging
logger = setup_logging()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Database: {settings.DATABASE_URL[:50]}..." if settings.DATABASE_URL else "Database: Not configured")
    
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # Continue startup even if DB fails - will retry on requests
    
    yield
    
    # Shutdown
    try:
        await close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {str(e)}")
    
    logger.info("Application shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Professional Vehicle Valuation Engine API - Single Source of Truth",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    servers=[
        {"url": settings.API_URL, "description": "Production API"},
        {"url": "http://localhost:8000", "description": "Development API"},
    ]
)

# Initialize rate limiter
app.state.limiter = limiter

# Add rate limiting middleware
app.add_middleware(SlowAPIMiddleware)

# CORS Configuration - Allow frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# Trusted Hosts - Security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# Rate Limiting exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for {request.client.host} on {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Reset": "60",
            "Retry-After": "60"
        },
        content={
            "detail": "Too many requests. Please try again later.",
            "retry_after": 60,
            "status_code": status.HTTP_429_TOO_MANY_REQUESTS
        }
    )

# ─── API Routers ──────────────────────────────────────────────

logger.info("Registering API routes...")

# Core routes
app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Authentication"])
app.include_router(users.router, prefix=settings.API_V1_PREFIX, tags=["Users"])

# Vehicle services
app.include_router(vehicles.router, prefix=settings.API_V1_PREFIX, tags=["Vehicles"])
app.include_router(valuations.router, prefix=settings.API_V1_PREFIX, tags=["Valuations"])
app.include_router(certificates.router, prefix=settings.API_V1_PREFIX, tags=["Certificates"])

# Payments
app.include_router(payments.router, prefix=settings.API_V1_PREFIX, tags=["Payments"])

# Fleet & Mileage
app.include_router(fleet.router, prefix=settings.API_V1_PREFIX, tags=["Fleet"])
app.include_router(mileage.router, prefix=settings.API_V1_PREFIX, tags=["Mileage"])

# Admin & Reports
app.include_router(admin.router, prefix=settings.API_V1_PREFIX, tags=["Admin"])
app.include_router(reports.router, prefix=settings.API_V1_PREFIX, tags=["Reports"])

# Webhooks (external)
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])

logger.info("All routes registered successfully")

# ─── Health & Root Endpoints ──────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "debug": settings.DEBUG,
        "timestamp": import_datetime_now().isoformat()
    }

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "docs": "/api/docs",
        "redoc": "/api/redoc",
        "health": "/health",
        "api_prefix": settings.API_V1_PREFIX
    }

@app.get("/api/version", tags=["Root"])
async def api_version():
    """Get API version information"""
    return {
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "api_version": "v1",
        "features": [
            "authentication",
            "vehicle_valuation",
            "certificate_generation",
            "mpesa_payments",
            "fleet_management",
            "mileage_calculation",
            "document_upload",
            "qr_verification"
        ]
    }

# ─── Global Exception Handlers ──────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format"""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail} on {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions"""
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "path": request.url.path
        }
    )

# ─── Middleware for Request Logging ──────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    import time
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log request details
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    # Add timing header
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    
    return response

# ─── Helper ─────────────────────────────────────────────────────

def import_datetime_now():
    """Import datetime.now for health check"""
    from datetime import datetime
    return datetime

# ─── Main Entry Point ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", settings.PORT))
    host = os.getenv("HOST", settings.HOST)
    debug = settings.DEBUG
    
    logger.info(f"Starting server on {host}:{port} (debug={debug})")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=settings.LOG_LEVEL.lower() if settings.LOG_LEVEL else "info",
        workers=int(os.getenv("WORKERS", settings.WORKERS or 1)),
        access_log=debug,
        use_colors=debug,
        timeout_keep_alive=30,
        loop="uvloop",
        http="httptools"
    )
