# app/core/database.py
# =============================================================================
# AUTO-V API - Database Core
# =============================================================================

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

# Create Base for models
Base = declarative_base()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # Convert postgresql:// to postgresql+asyncpg:// if needed
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = None
async_session_maker = None

if DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def is_database_configured() -> bool:
    """Check if database is configured"""
    return DATABASE_URL is not None and engine is not None


async def init_db():
    """Initialize database connection"""
    if engine is None:
        return
    
    # Test connection
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def close_db():
    """Close database connections"""
    if engine is not None:
        await engine.dispose()


async def check_db_health() -> bool:
    """Check database health"""
    if engine is None:
        return False
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False


async def get_db() -> AsyncSession:
    """Get database session"""
    if async_session_maker is None:
        raise Exception("Database not configured")
    
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
