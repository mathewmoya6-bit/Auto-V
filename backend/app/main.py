# app/main.py
# =============================================================================
# AUTO-V API - FastAPI Entrypoint
# =============================================================================

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    """Lifespan context manager for startup and shutdown."""
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📌 Environment: {settings.ENV}")
    logger.info("=" * 60)
    
    # Initialize Supabase
    if settings.supabase_configured:
        try:
            success = init_supabase()
            if success:
                logger.info("✅ Supabase initialized successfully")
            else:
                logger.warning("⚠️  Supabase initialization failed")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase: {e}")
    else:
        logger.warning("⚠️  Supabase not configured")
    
    logger.info(f"📊 Database status: {'✅ Connected' if is_configured() else '❌ Not configured'}")
    logger.info("=" * 60)
    
    yield
    
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
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# ─── Request Logging Middleware ─────────────────────────────────────

@app.middleware("http")
async def log_requests(request, call_next):
    import time
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)"
    )
    
    return response


# ─── API Routers ─────────────────────────────────────────────────────

app.include_router(api_router, prefix="/api/v1")


# ─── Root Endpoint ──────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy" if is_configured() else "degraded",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


logger.info("✅ AUTO-V API initialized successfully")
