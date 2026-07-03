# app/core/database.py
# =============================================================================
# AUTO-V API - Database Configuration
# =============================================================================

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.models import Base

logger = logging.getLogger(__name__)


# =============================================================================
# DATABASE URL VALIDATION
# =============================================================================

def get_database_url() -> Optional[str]:
    """
    Get the database URL from settings with validation and fallback.
    
    Returns:
        A valid database URL or None if not configured.
    """
    url = settings.DATABASE_URL
    
    # If no DATABASE_URL is set, check environment
    if not url:
        # In production, this is a critical error
        if settings.is_production():
            logger.error("❌ DATABASE_URL is required in production!")
            logger.error("   Please set DATABASE_URL in your Render environment variables.")
            logger.error("   Format: postgresql+asyncpg://user:password@host:5432/database")
            return None
        
        # In development, use SQLite as fallback
        logger.warning("⚠️  DATABASE_URL not set. Using SQLite for development.")
        logger.warning("   For production, set DATABASE_URL in your environment.")
        return "sqlite+aiosqlite:///./app.db"
    
    # Ensure asyncpg driver is used for PostgreSQL
    if url.startswith("postgresql://") and "+" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        logger.info(f"✅ Added asyncpg driver to DATABASE_URL")
    
    return url


# =============================================================================
# CREATE DATABASE ENGINE
# =============================================================================

def create_database_engine() -> Optional[AsyncEngine]:
    """
    Create and configure the async SQLAlchemy engine.
    Returns None if database is not configured.
    """
    database_url = get_database_url()
    
    if not database_url:
        logger.error("❌ Cannot create database engine: No DATABASE_URL provided")
        return None
    
    try:
        engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=getattr(settings, 'DB_POOL_SIZE', 5),
            max_overflow=getattr(settings, 'DB_MAX_OVERFLOW', 10),
            pool_recycle=3600,
            pool_timeout=30,
        )
        logger.info(f"✅ Database engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"❌ Failed to create database engine: {e}")
        return None


# =============================================================================
# INITIALIZE DATABASE COMPONENTS
# =============================================================================

# Create the engine with proper error handling
engine = create_database_engine()

# Create async session factory if engine exists
if engine:
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    logger.info("✅ AsyncSessionLocal created successfully")
else:
    AsyncSessionLocal = None
    logger.warning("⚠️  AsyncSessionLocal is None - database features disabled")


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

async def init_db() -> None:
    """
    Create any tables defined in models.py that don't already exist.
    This is safe to call even if tables already exist.
    """
    if engine is None:
        logger.error("❌ Cannot initialize database: Engine is None")
        logger.error("   Please set DATABASE_URL in your environment variables")
        return
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables verified/created")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """
    Close database connections.
    Call this during application shutdown.
    """
    if engine:
        await engine.dispose()
        logger.info("✅ Database connections closed")


# =============================================================================
# DATABASE DEPENDENCY
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields an AsyncSession per request.
    
    Usage:
        from app.core.database import get_db
        from fastapi import Depends
        
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    if AsyncSessionLocal is None:
        logger.error("❌ Database not configured. Cannot provide session.")
        raise RuntimeError(
            "Database not configured. Please set DATABASE_URL in your environment. "
            "For production on Render, add DATABASE_URL to your environment variables."
        )
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"❌ Database error: {e}")
            raise
        finally:
            await session.close()


# =============================================================================
# DATABASE STATUS CHECK
# =============================================================================

def is_database_configured() -> bool:
    """
    Check if the database is properly configured.
    """
    return engine is not None and AsyncSessionLocal is not None


def get_db_status() -> dict:
    """
    Get database connection status for health checks.
    """
    return {
        "configured": is_database_configured(),
        "url_configured": settings.DATABASE_URL is not None and settings.DATABASE_URL != "",
        "engine_created": engine is not None,
        "session_factory_created": AsyncSessionLocal is not None,
        "environment": getattr(settings, 'ENV', 'unknown'),
    }


async def check_db_health() -> bool:
    """
    Check if the database connection is healthy.
    Returns True if healthy, False otherwise.
    """
    if engine is None:
        return False
    
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False


# =============================================================================
# CONTEXT MANAGER FOR DATABASE SESSIONS
# =============================================================================

@asynccontextmanager
async def get_db_context():
    """
    Context manager for database sessions.
    
    Usage:
        async with get_db_context() as db:
            result = await db.execute(...)
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
