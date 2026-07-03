# app/main.py - FastAPI Application Entry Point
# =============================================================================
# AUTO-V API - Main Application
# =============================================================================

import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_db, close_db, is_database_configured

# =============================================================================
# SETUP LOGGING
# =============================================================================

logger = setup_logging()

# =============================================================================
# RATE LIMITER
# =============================================================================

limiter = Limiter(key_func=get_remote_address)

# =============================================================================
# LIFESPAN MANAGER
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # --- STARTUP ---
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📌 Environment: {settings.ENV}")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info(f"🗄️  Database configured: {is_database_configured()}")
    
    # Log CORS settings for debugging
    logger.info(f"🌐 CORS_ORIGINS: {settings.CORS_ORIGINS}")
    logger.info(f"🔒 ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    
    if settings.DATABASE_URL:
        # Mask password for security
        masked_url = settings.DATABASE_URL[:30] + "..." if len(settings.DATABASE_URL) > 30 else settings.DATABASE_URL
        logger.info(f"📊 Database: {masked_url}")
    
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        # Continue startup even if DB fails - will retry on requests
    
    logger.info("=" * 60)
    
    yield
    
    # --- SHUTDOWN ---
    try:
        await close_db()
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {str(e)}")
    
    logger.info("👋 Application shutdown complete")

# =============================================================================
# CREATE FASTAPI APP
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Professional Vehicle Valuation Engine API - Single Source of Truth",
    docs_url="/docs" if settings.ENABLE_SWAGGER else None,
    redoc_url="/redoc" if settings.ENABLE_SWAGGER else None,
    openapi_url="/openapi.json" if settings.ENABLE_SWAGGER else None,
    lifespan=lifespan,
    servers=[
        {"url": settings.API_URL, "description": "Production API"},
        {"url": "http://localhost:8000", "description": "Development API"},
    ],
)

# =============================================================================
# RATE LIMITING MIDDLEWARE
# =============================================================================

app.state.limiter = limiter
if settings.ENABLE_RATE_LIMITING:
    app.add_middleware(SlowAPIMiddleware)
    logger.info("✅ Rate limiting enabled")

# =============================================================================
# CORS MIDDLEWARE - WITH FALLBACK
# =============================================================================

# Get CORS origins with fallback
cors_origins = getattr(settings, 'CORS_ORIGINS', ["*"])
if not cors_origins or cors_origins == []:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Response-Time",
    ],
)
logger.info(f"✅ CORS enabled with origins: {cors_origins}")

# =============================================================================
# TRUSTED HOST MIDDLEWARE - WITH FALLBACK
# =============================================================================

if settings.is_production():
    allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', ["*"])
    if not allowed_hosts or allowed_hosts == []:
        allowed_hosts = ["*"]
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts,
    )
    logger.info(f"✅ Trusted hosts: {allowed_hosts}")

# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    logger.warning(f"🚫 Rate limit exceeded for {request.client.host} on {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Reset": "60",
            "Retry-After": "60",
        },
        content={
            "detail": "Too many requests. Please try again later.",
            "retry_after": 60,
            "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format."""
    logger.warning(f"⚠️  HTTP exception: {exc.status_code} - {exc.detail} on {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions."""
    logger.error(f"💥 Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "path": request.url.path,
        },
    )

# =============================================================================
# REQUEST LOGGING MIDDLEWARE
# =============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
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
            "client_ip": request.client.host if request.client else "unknown",
        },
    )
    
    # Add timing header
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    
    return response

# =============================================================================
# IMPORT ROUTERS - GRACEFUL HANDLING
# =============================================================================

logger.info("📦 Registering API routes...")

# Import all routers with graceful fallback
try:
    from app.api.v1.routes.auth import router as auth_router
    logger.info("✅ Auth routes imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import auth routes: {e}")
    auth_router = None

try:
    from app.api.v1.routes.users import router as users_router
    logger.info("✅ Users routes imported successfully")
except ImportError:
    users_router = None
    logger.warning("⚠️  Users routes not found")

try:
    from app.api.v1.routes.vehicles import router as vehicles_router
    logger.info("✅ Vehicles routes imported successfully")
except ImportError:
    vehicles_router = None
    logger.warning("⚠️  Vehicles routes not found")

try:
    from app.api.v1.routes.valuations import router as valuations_router
    logger.info("✅ Valuations routes imported successfully")
except ImportError:
    valuations_router = None
    logger.warning("⚠️  Valuations routes not found")

try:
    from app.api.v1.routes.payments import router as payments_router
    logger.info("✅ Payments routes imported successfully")
except ImportError:
    payments_router = None
    logger.warning("⚠️  Payments routes not found")

try:
    from app.api.v1.routes.reports import router as reports_router
    logger.info("✅ Reports routes imported successfully")
except ImportError:
    reports_router = None
    logger.warning("⚠️  Reports routes not found")

try:
    from app.api.v1.routes.webhooks import router as webhooks_router
    logger.info("✅ Webhooks routes imported successfully")
except ImportError:
    webhooks_router = None
    logger.warning("⚠️  Webhooks routes not found")

# Try to import optional modules
try:
    from app.api.v1.routes.certificates import router as certificates_router
    logger.info("✅ Certificates routes imported successfully")
except ImportError:
    certificates_router = None
    logger.warning("⚠️  Certificates routes not found")

try:
    from app.api.v1.routes.mileage import router as mileage_router
    logger.info("✅ Mileage routes imported successfully")
except ImportError:
    mileage_router = None
    logger.warning("⚠️  Mileage routes not found")

try:
    from app.api.v1.routes.fleet import router as fleet_router
    logger.info("✅ Fleet routes imported successfully")
except ImportError:
    fleet_router = None
    logger.warning("⚠️  Fleet routes not found")

try:
    from app.api.v1.routes.admin import router as admin_router
    logger.info("✅ Admin routes imported successfully")
except ImportError:
    admin_router = None
    logger.warning("⚠️  Admin routes not found")

# =============================================================================
# REGISTER ROUTES
# =============================================================================

# Core routes
if auth_router:
    app.include_router(auth_router, prefix=settings.API_V1_PREFIX, tags=["Authentication"])
if users_router:
    app.include_router(users_router, prefix=settings.API_V1_PREFIX, tags=["Users"])
if vehicles_router:
    app.include_router(vehicles_router, prefix=settings.API_V1_PREFIX, tags=["Vehicles"])
if valuations_router:
    app.include_router(valuations_router, prefix=settings.API_V1_PREFIX, tags=["Valuations"])
if payments_router:
    app.include_router(payments_router, prefix=settings.API_V1_PREFIX, tags=["Payments"])
if reports_router:
    app.include_router(reports_router, prefix=settings.API_V1_PREFIX, tags=["Reports"])

# Webhooks (external)
if webhooks_router:
    app.include_router(webhooks_router, prefix="/api/webhooks", tags=["Webhooks"])

# Optional routes
if certificates_router:
    app.include_router(certificates_router, prefix=settings.API_V1_PREFIX, tags=["Certificates"])
if mileage_router:
    app.include_router(mileage_router, prefix=settings.API_V1_PREFIX, tags=["Mileage"])
if fleet_router:
    app.include_router(fleet_router, prefix=settings.API_V1_PREFIX, tags=["Fleet"])
if admin_router:
    app.include_router(admin_router, prefix=settings.API_V1_PREFIX, tags=["Admin"])

logger.info("✅ All routes registered successfully")

# =============================================================================
# HEALTH & ROOT ENDPOINTS
# =============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "debug": settings.DEBUG,
        "database_configured": is_database_configured(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "docs": "/docs" if settings.ENABLE_SWAGGER else None,
        "redoc": "/redoc" if settings.ENABLE_SWAGGER else None,
        "health": "/health",
        "api_prefix": settings.API_V1_PREFIX,
    }


@app.get("/api/version", tags=["Root"])
async def api_version():
    """Get API version information."""
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
            "qr_verification",
        ],
    }

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", settings.PORT))
    host = os.getenv("HOST", settings.HOST)
    debug = settings.DEBUG
    
    logger.info(f"🚀 Starting server on {host}:{port} (debug={debug})")
    
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
        http="httptools",
    )
