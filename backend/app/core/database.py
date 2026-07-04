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
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── DATABASE URL ──────────────────────────────────────────────────

# Your DATABASE_URL from Render (correct format)
DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL:
    # Mask password for logging
    masked_url = DATABASE_URL[:30] + "..." if len(DATABASE_URL) > 30 else DATABASE_URL
    logger.info(f"📊 Database URL: {masked_url}")
else:
    logger.error("❌ DATABASE_URL is not configured!")

# ─── CREATE ENGINE ──────────────────────────────────────────────────

# ✅ Correct: No sslmode parameter here - it's in the connection string
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG if hasattr(settings, 'DEBUG') else False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_timeout=30,
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

logger.info("✅ AsyncSessionLocal created successfully")

# ─── BASE MODEL ──────────────────────────────────────────────────

Base = declarative_base()


# ─── DATABASE DEPENDENCY ──────────────────────────────────────────

async def get_db():
    """
    FastAPI dependency for database session.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
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


# ─── DATABASE STATUS CHECKS ──────────────────────────────────────

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
