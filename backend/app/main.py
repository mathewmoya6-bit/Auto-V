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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Tables are managed via mileage_schema.sql / Alembic migrations.
    """
    # STARTUP
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
    
    # SHUTDOWN
    logger.info("🛑 Shutting down AUTO-V API...")
    await close_db()
    logger.info("✅ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="AUTO-V API",
    version="3.1.0",
    description="AUTO-V Professional Valuation Engine API",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AUTO-V API",
        "version": "3.1.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health():
    """
    Health check endpoint.
    Returns service status and database connectivity.
    """
    db_ok = await check_db_health() if is_database_configured() else False
    
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "service": "AUTO-V API",
        "version": "3.1.0"
    }


@app.get("/ready")
async def ready():
    """
    Readiness probe endpoint.
    Checks if the service is ready to accept traffic.
    """
    db_ok = await check_db_health() if is_database_configured() else False
    
    if db_ok:
        return {"ready": True}
    else:
        return {"ready": False, "reason": "Database not available"}, 503
