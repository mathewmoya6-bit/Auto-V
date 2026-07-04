# app/core/database.py
# =============================================================================
# AUTO-V API - Database Configuration (Supabase Postgres, async via asyncpg)
# =============================================================================

import re
import logging
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


def _build_database_url(raw_url: str) -> tuple[str, dict]:
    """Normalize a Postgres URL for async SQLAlchemy + asyncpg (Render/Supabase-safe)."""
    url = raw_url.strip()

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if "sslmode" in url or "ssl=" in url:
        url = re.sub(r"[?&]sslmode=[^&]*", "", url)
        url = re.sub(r"[?&]ssl=[^&]*", "", url)
        url = url.rstrip("?&")

    return url, {"ssl": True}  # Supabase Postgres requires TLS


if not settings.database_configured():
    logger.error("DATABASE_URL is not configured!")
    raise RuntimeError(
        "DATABASE_URL is not configured. Set it to your Supabase Postgres "
        "connection string, e.g. postgresql://postgres:<password>@<host>:5432/postgres"
    )

DATABASE_URL, CONNECT_ARGS = _build_database_url(settings.DATABASE_URL)
logger.info("Database URL configured (driver=asyncpg, password hidden)")

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=3600,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    connect_args=CONNECT_ARGS,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def close_db():
    await engine.dispose()
    logger.info("Database connections closed")


async def check_db_health() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def is_database_configured() -> bool:
    return settings.database_configured() and engine is not None
