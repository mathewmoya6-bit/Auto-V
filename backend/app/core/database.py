# app/core/database.py
# =============================================================================
# AUTO-V API - Database Configuration
# =============================================================================

import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── DATABASE URL ──────────────────────────────────────────────────

# Your DATABASE_URL from Render (already correct)
DATABASE_URL = settings.DATABASE_URL

logger.info(f"📊 Database URL configured (password hidden): {DATABASE_URL[:30]}...")

# ─── CREATE ENGINE ──────────────────────────────────────────────────

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    # ✅ No sslmode parameter here - it's handled in the connection string
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
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


def is_database_configured() -> bool:
    """Check if database is configured."""
    return DATABASE_URL is not None and DATABASE_URL != ""


async def init_db():
    """Initialize database (create tables if they don't exist)."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")


async def close_db():
    """Close database connections."""
    await engine.dispose()
    logger.info("✅ Database connections closed")


# ─── DATABASE STATUS ──────────────────────────────────────────────

def get_db_status() -> dict:
    """Get database connection status."""
    return {
        "configured": is_database_configured(),
        "url_configured": DATABASE_URL is not None and DATABASE_URL != "",
        "engine_created": engine is not None,
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
