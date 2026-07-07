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
    
    logger.info(f"📊 Database status: {'✅ Connected' if
