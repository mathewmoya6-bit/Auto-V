# app/main.py
# =============================================================================
# AUTO-V API - FastAPI entrypoint
# =============================================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import check_db_health, close_db, init_db, is_database_configured

# =============================================================================
# Logging Configuration
# =============================================================================
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan Manager
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Tables are managed via mileage_schema.sql / Alembic migrations.
    
    Startup:
        - Initialize database tables
        - Check database health
        - Log connection status
    
    Shutdown:
        - Close database connections
        - Clean up resources
    """
    # ── STARTUP ──
    logger.info("🚀 Starting AUTO-V API...")
    
    if is_database_configured():
        try:
            # Initialize database tables if needed
            await init_db()
            logger.info("✅ Database initialized successfully")
            
            # Check database health
            db_ok = await check_db_health()
            if db_ok:
                logger.info("✅ Database connection healthy")
            else:
                logger.warning("⚠️  Database health check failed - continuing with degraded functionality")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            logger.warning("⚠️  Continuing with degraded functionality")
    else:
        logger.warning("⚠️  Database not configured - running in degraded mode")
    
    yield  # Application runs here
    
    # ── SHUTDOWN ──
    logger.info("🛑 Shutting down AUTO-V API...")
    await close_db()
    logger.info("✅ Shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title="AUTO-V API",
    version="3.1.0",
    description="AUTO-V Professional Valuation Engine API",
    lifespan=lifespan,
)


# =============================================================================
# CORS Middleware
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# API Routers
# =============================================================================
app.include_router(api_router, prefix="/api/v1")


# =============================================================================
# Root Endpoint
# =============================================================================
@app.get("/")
async def root():
    """
    Root endpoint.
    
    Returns:
        Service information and status
    """
    return {
        "service": "AUTO-V API",
        "version": "3.1.0",
        "docs": "/docs",
        "status": "running"
    }


# =============================================================================
# Health Check Endpoint
# =============================================================================
@app.get("/health")
async def health():
    """
    Health check endpoint.
    
    Returns service status and database connectivity.
    
    Returns:
        dict: Health status with database connectivity
    """
    db_ok = await check_db_health() if is_database_configured() else False
    
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "service": "AUTO-V API",
        "version": "3.1.0"
    }


# =============================================================================
# Readiness Probe Endpoint
# =============================================================================
@app.get("/ready")
async def ready():
    """
    Readiness probe endpoint.
    
    Checks if the service is ready to accept traffic.
    
    Returns:
        dict: Readiness status
        HTTP 503: If database is not available
    """
    db_ok = await check_db_health() if is_database_configured() else False
    
    if db_ok:
        return {"ready": True}
    else:
        return {"ready": False, "reason": "Database not available"}, 503
