# app/main.py
# =============================================================================
# AUTO-V API - FastAPI Entrypoint
# =============================================================================

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import init_supabase, is_configured
from app.core.logging import get_logger, setup_logging

# ─── Setup Logging ──────────────────────────────────────────────────

setup_logging()
logger = get_logger(__name__)


# ─── Lifespan Manager ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Startup:
        - Initialize Supabase clients
        - Log configuration status
    
    Shutdown:
        - Clean up resources
    """
    # ─── STARTUP ──────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📌 Environment: {settings.ENV}")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info(f"🌐 CORS Origins: {settings.CORS_ORIGINS}")
    logger.info("=" * 60)
    
    # Initialize Supabase
    if settings.supabase_configured:
        try:
            success = init_supabase()
            if success:
                logger.info("✅ Supabase initialized successfully")
            else:
                logger.warning("⚠️  Supabase initialization failed - continuing with degraded functionality")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase: {e}")
            logger.warning("⚠️  Continuing with degraded functionality")
    else:
        logger.warning("⚠️  Supabase not configured - running in degraded mode")
    
    logger.info(f"📊 Database status: {'✅ Connected' if is_configured() else '❌ Not configured'}")
    logger.info("=" * 60)
    
    yield  # Application runs here
    
    # ─── SHUTDOWN ─────────────────────────────────────────────────────
    logger.info("🛑 Shutting down AUTO-V API...")
    logger.info("✅ Shutdown complete")


# ─── FastAPI Application ────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Professional Vehicle Valuation Engine API",
    docs_url="/docs" if settings.ENABLE_SWAGGER else None,
    redoc_url="/redoc" if settings.ENABLE_SWAGGER else None,
    openapi_url="/openapi.json" if settings.ENABLE_SWAGGER else None,
    lifespan=lifespan,
)


# ─── CORS Middleware ─────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS if settings.CORS_ALLOW_METHODS else ["*"],
    allow_headers=settings.CORS_ALLOW_HEADERS if settings.CORS_ALLOW_HEADERS else ["*"],
)


# ─── Request Logging Middleware ─────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests with timing.
    """
    import time
    
    start_time = time.time()
    
    # Log request
    logger.info(
        f"➡️ {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        }
    )
    
    try:
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"⬅️ {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration": round(process_time, 3),
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(
            f"❌ {request.method} {request.url.path} - Error: {str(e)}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
            },
            exc_info=True
        )
        raise


# ─── Error Handlers ─────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors with detailed messages.
    """
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={
            "path": request.url.path,
            "errors": exc.errors(),
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "status_code": 422,
            "detail": "Validation error",
            "errors": exc.errors(),
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler for unhandled errors.
    """
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # In production, don't expose internal error details
    error_detail = str(exc) if settings.DEBUG else "An internal server error occurred"
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "detail": error_detail,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    )


# ─── API Routers ─────────────────────────────────────────────────────

app.include_router(api_router, prefix="/api/v1")


# ─── Root Endpoint ──────────────────────────────────────────────────

@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with service information.
    
    Returns:
        Service information and status
    """
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "docs": "/docs" if settings.ENABLE_SWAGGER else "disabled",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ─── Health Check Endpoint ──────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns service status and database connectivity.
    
    Returns:
        dict: Health status with database connectivity
    """
    db_ok = is_configured()
    
    return {
        "status": "healthy" if db_ok else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "database": {
            "configured": db_ok,
            "connected": db_ok,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ─── Readiness Probe Endpoint ──────────────────────────────────────

@app.get("/ready", tags=["System"])
async def readiness_check():
    """
    Readiness probe endpoint for Kubernetes/Render.
    
    Checks if the service is ready to accept traffic.
    
    Returns:
        dict: Readiness status
        HTTP 503: If database is not available
    """
    db_ok = is_configured()
    
    if db_ok:
        return {
            "ready": True,
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    else:
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "status": "not ready",
                "reason": "Database not available",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )


# ─── Liveness Probe Endpoint ──────────────────────────────────────

@app.get("/live", tags=["System"])
async def liveness_check():
    """
    Liveness probe endpoint for Kubernetes/Render.
    
    Checks if the service is alive.
    
    Returns:
        dict: Liveness status
    """
    return {
        "alive": True,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ─── Debug Endpoint (Development Only) ─────────────────────────────

if settings.DEBUG:
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """
        Debug endpoint to show configuration (development only).
        """
        return {
            "app": {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.ENV,
                "debug": settings.DEBUG,
            },
            "database": {
                "configured": is_configured(),
                "url": "***hidden***" if settings.DATABASE_URL else None,
            },
            "supabase": {
                "configured": settings.supabase_configured,
                "url": settings.SUPABASE_URL[:30] + "..." if settings.SUPABASE_URL else None,
            },
            "features": {
                "swagger": settings.ENABLE_SWAGGER,
                "metrics": settings.ENABLE_METRICS,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


# ─── Module Logger ──────────────────────────────────────────────────

logger.info("✅ AUTO-V API initialized successfully")
logger.info(f"📚 API Documentation: /docs")
logger.info(f"🔗 Health Check: /health")
logger.info(f"📌 API Prefix: /api/v1")
