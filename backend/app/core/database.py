# app/core/database.py
# =============================================================================
# Database Connection & Session Management
# =============================================================================

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData, event
import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create Base with naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

# Database engine
if settings.DATABASE_URL:
    # Convert asyncpg URL to asyncpg format if needed
    database_url = settings.DATABASE_URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # 🔧 FIX: Disable prepared statement cache for Supabase/PgBouncer
    engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=5,  # Reduced for PgBouncer
        max_overflow=10,
        # ⚡ Critical fix: Disable statement caching
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": 0,  # This disables prepared statements
            "command_timeout": 60,
            "server_settings": {
                "application_name": "auto-v-api"
            }
        }
    )
    
    # Alternative: Listen for connection events to reset cache
    @event.listens_for(engine.sync_engine, "connect")
    def connect(dbapi_connection, connection_record):
        # Disable prepared statements at the connection level
        cursor = dbapi_connection.cursor()
        cursor.execute("SET statement_timeout = '60s'")
        cursor.close()
        
else:
    engine = None
    logger.warning("⚠️ DATABASE_URL not set - running in demo mode")

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

def is_database_configured() -> bool:
    """Check if database is configured."""
    return engine is not None

async def init_db():
    """Initialize database connection."""
    if not is_database_configured():
        logger.warning("⚠️ Database not configured - skipping initialization")
        return
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        raise

async def close_db():
    """Close database connection."""
    if engine:
        await engine.dispose()
        logger.info("✅ Database connection closed")

async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
