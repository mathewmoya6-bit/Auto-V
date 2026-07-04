# main.py
# =============================================================================
# AUTO-V API - Main Application Entry Point
# =============================================================================

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db, is_database_configured
from app.api.v1.routes import auth, vehicles, valuations, inspections, mileage, fleet, certificates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Database configured: {is_database_configured()}")
    logger.info("=" * 60)

    if is_database_configured():
        try:
            await init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)

    yield

    await close_db()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AUTO-V: Vehicle Valuation, Inspection, Fleet Management & Verification API",
    docs_url="/docs" if settings.ENABLE_SWAGGER else None,
    redoc_url="/redoc" if settings.ENABLE_SWAGGER else None,
    openapi_url="/openapi.json" if settings.ENABLE_SWAGGER else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(vehicles.router, prefix=settings.API_V1_PREFIX)
app.include_router(valuations.router, prefix=settings.API_V1_PREFIX)
app.include_router(inspections.router, prefix=settings.API_V1_PREFIX)
app.include_router(mileage.router, prefix=settings.API_V1_PREFIX)
app.include_router(fleet.router, prefix=settings.API_V1_PREFIX)
app.include_router(certificates.router, prefix=settings.API_V1_PREFIX)

logger.info("All routes registered successfully")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "database_configured": is_database_configured(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api_prefix": settings.API_V1_PREFIX,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=port,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1,
    )
