# app/core/database.py
# =============================================================================
# AUTO-V API - Database Core
# =============================================================================

import os
import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ─── Base for Models ──────────────────────────────────────────────
Base = declarative_base()

# ─── Database Configuration ──────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")

# Convert postgresql:// to postgresql+asyncpg:// if needed
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# ─── Engine and Session Factory ─────────────────────────────────
engine: AsyncEngine = None
async_session_maker: async_sessionmaker = None

if DATABASE_URL:
    try:
        engine = create_async_engine(
            DATABASE_URL,
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_pre_ping=True,
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )
        
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        logger.info("✅ Database engine configured successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create database engine: {e}")
        engine = None
        async_session_maker = None
else:
    logger.warning("⚠️  DATABASE_URL not set - running without database")


# ─── Helper Functions ────────────────────────────────────────────

def is_database_configured() -> bool:
    """Check if database is configured"""
    return DATABASE_URL is not None and engine is not None


async def init_db():
    """
    Initialize database connection
    """
    if engine is None:
        logger.warning("⚠️  Database not configured, skipping initialization")
        return
    
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        raise


async def close_db():
    """
    Close database connections
    """
    if engine is not None:
        try:
            await engine.dispose()
            logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing database connections: {e}")


async def check_db_health() -> bool:
    """
    Check database health
    
    Returns:
        True if database is healthy, False otherwise
    """
    if engine is None:
        return False
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False


async def get_db() -> AsyncSession:
    """
    Get database session (dependency injection)
    
    Yields:
        AsyncSession: Database session
    """
    if async_session_maker is None:
        raise Exception("Database not configured")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database session error: {e}")
            raise
        finally:
            await session.close()


async def get_db_connection():
    """
    Get raw database connection (for admin/special operations)
    """
    if engine is None:
        raise Exception("Database not configured")
    
    async with engine.connect() as conn:
        return conn
