# app/core/database.py
# =============================================================================
# AUTO-V API - Database Configuration
# =============================================================================

import logging
import re
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── DATABASE URL ──────────────────────────────────────────────────

DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL is not configured!")
    raise RuntimeError("DATABASE_URL is not configured")

# ✅ Remove any sslmode from URL
if DATABASE_URL:
    if "sslmode=require" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("sslmode=require", "ssl=require")
        logger.info("✅ Fixed sslmode=require -> ssl=require")
    
    if "sslmode" in DATABASE_URL:
        DATABASE_URL = re.sub(r'\?sslmode=[^&]*', '', DATABASE_URL)
        DATABASE_URL = re.sub(r'&sslmode=[^&]*', '', DATABASE_URL)
        logger.info("✅ Removed sslmode from DATABASE_URL")

logger.info(f"📊 Database URL configured (password hidden)")

# ─── CREATE ENGINE ──────────────────────────────────────────────────

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=3600,
    pool_timeout=settings.DB_POOL_TIMEOUT,
)

logger.info("✅ Database engine created successfully")

# ─── SESSION FACTORY ──────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


# ─── DATABASE DEPENDENCY ──────────────────────────────────────────

async def get_db():
    """FastAPI dependency for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ─── CONTEXT MANAGER ──────────────────────────────────────────────

@asynccontextmanager
async def get_db_context():
    """
    Context manager for database sessions.
    
    Usage:
        async with get_db_context() as session:
            result = await session.execute(...)
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not configured")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─── DATABASE INITIALIZATION ──────────────────────────────────────

async def init_db():
    """Initialize database (create tables if they don't exist)."""
    if engine is None:
        logger.error("❌ Cannot initialize database: Engine is None")
        return
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        raise


async def close_db():
    """Close database connections."""
    if engine:
        await engine.dispose()
        logger.info("✅ Database connections closed")


def is_database_configured() -> bool:
    """Check if the database is properly configured."""
    return DATABASE_URL is not None and DATABASE_URL != "" and engine is not None


def get_db_status() -> dict:
    """Get database connection status."""
    return {
        "configured": is_database_configured(),
        "url_configured": DATABASE_URL is not None and DATABASE_URL != "",
        "engine_created": engine is not None,
        "session_factory_created": AsyncSessionLocal is not None,
    }


async def check_db_health() -> bool:
    """Check if the database connection is healthy."""
    if engine is None:
        return False
    
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"❌ Database health check failed: {str(e)}")
        return False
