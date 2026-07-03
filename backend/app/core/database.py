# app/core/database.py
# =============================================================================
# AUTO-V API - Database Configuration (Supabase PostgreSQL)
# =============================================================================

import os
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# =============================================================================
# DATABASE URL FROM SUPABASE CREDENTIALS
# =============================================================================

# Your Supabase credentials
USER = "postgres"
PASSWORD = "22313261@abcd"  # Contains @ which needs URL encoding
HOST = "db.tsvejnzxrxrrecgquxbq.supabase.co"
PORT = "5432"
DBNAME = "postgres"

# URL-encode special characters in password
# @ becomes %40
ENCODED_PASSWORD = PASSWORD.replace("@", "%40")

# Construct the async SQLAlchemy connection string
# Using asyncpg driver (required for async operations)
# sslmode=require ensures SSL connection to Supabase
DATABASE_URL = f"postgresql+asyncpg://{USER}:{ENCODED_PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

# Alternatively, use settings.DATABASE_URL if set in environment
# DATABASE_URL = settings.DATABASE_URL or DATABASE_URL

logger.info(f"🔗 Database URL configured (password hidden): {DATABASE_URL[:30]}...")

# =============================================================================
# CREATE DATABASE ENGINE
# =============================================================================

def create_engine_pool() -> Optional[AsyncEngine]:
    """
    Create and configure the async SQLAlchemy engine for Supabase.
    Returns None if database is not configured.
    """
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL is not configured!")
        return None

    try:
        # Create async engine with connection pooling
        # QueuePool is default for PostgreSQL, optimized for production
        engine = create_async_engine(
            DATABASE_URL,
            echo=settings.DEBUG if hasattr(settings, 'DEBUG') else False,
            pool_pre_ping=True,      # Check connection before using (handles disconnects)
            pool_size=10,             # Max connections in pool
            max_overflow=20,          # Extra connections if pool is full
            pool_recycle=3600,        # Recycle connections after 1 hour
            pool_timeout=30,          # Timeout for getting connection from pool
        )
        logger.info("✅ Database engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"❌ Failed to create database engine: {str(e)}")
        return None

# =============================================================================
# INITIALIZE DATABASE COMPONENTS
# =============================================================================

# Create the engine
engine = create_engine_pool()

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

# Create declarative base for models
Base = declarative_base()

# =============================================================================
# DATABASE DEPENDENCY (for FastAPI routes)
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    if AsyncSessionLocal is None:
        logger.error("❌ Database not configured. Cannot provide session.")
        raise RuntimeError(
            "Database not configured. Please check DATABASE_URL."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"❌ Database error: {str(e)}")
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Unexpected error: {str(e)}")
            raise
        finally:
            await session.close()

# =============================================================================
# DATABASE INITIALIZATION & CLEANUP
# =============================================================================

async def init_db() -> None:
    """
    Create database tables if they don't exist.
    Call this during application startup.
    """
    if engine is None:
        logger.error("❌ Cannot initialize database: Engine is None")
        return

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables verified/created")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
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
# DATABASE STATUS CHECKS
# =============================================================================

def is_database_configured() -> bool:
    """Check if the database is properly configured."""
    return engine is not None and AsyncSessionLocal is not None

def get_db_status() -> dict:
    """Get database connection status for health checks."""
    return {
        "configured": is_database_configured(),
        "url_configured": DATABASE_URL is not None and DATABASE_URL != "",
        "engine_created": engine is not None,
        "session_factory_created": AsyncSessionLocal is not None,
        "environment": getattr(settings, 'ENV', 'unknown'),
    }

async def check_db_health() -> bool:
    """Check if the database connection is healthy."""
    if engine is None:
        return False

    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"❌ Database health check failed: {str(e)}")
        return False

# =============================================================================
# CONTEXT MANAGER FOR DATABASE SESSIONS
# =============================================================================

from contextlib import asynccontextmanager

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
