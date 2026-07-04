# main.py
# =============================================================================
# AUTO-V API - Main Application Entry Point
# =============================================================================

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db, is_database_configured
from app.api.v1.routes import auth, mileage

# ─── Setup Logging ──────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Lifespan Manager ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📌 Environment: {settings.ENV}")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info(f"🗄️  Database configured: {is_database_configured()}")
    logger.info(f"🌐 CORS_ORIGINS: {settings.CORS_ORIGINS}")
    logger.info("=" * 60)
    
    if is_database_configured():
        try:
            await init_db()
            logger.info("✅ Database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {str(e)}")
    
    yield
    
    # Shutdown
    await close_db()
    logger.info("👋 Application shutdown complete")


# ─── Create FastAPI App ────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Professional Vehicle Valuation Engine API",
    docs_url="/docs" if settings.ENABLE_SWAGGER else None,
    redoc_url="/redoc" if settings.ENABLE_SWAGGER else None,
    openapi_url="/openapi.json" if settings.ENABLE_SWAGGER else None,
    lifespan=lifespan,
)


# ─── CORS Middleware ───────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Response-Time"],
)


# ─── Register Routes ──────────────────────────────────────────────

app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Authentication"])
app.include_router(mileage.router, prefix=settings.API_V1_PREFIX, tags=["Mileage"])

logger.info("✅ All routes registered successfully")


# ─── Health & Root Endpoints ──────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "debug": settings.DEBUG,
        "database_configured": is_database_configured(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "docs": "/docs",
        "health": "/health",
        "api_prefix": settings.API_V1_PREFIX,
    }


# ─── Main Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", settings.PORT))
    host = os.getenv("HOST", settings.HOST)
    debug = settings.DEBUG
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1,
    )
