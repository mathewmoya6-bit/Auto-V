# app/core/database.py
# =============================================================================
# AUTO-V API - Database Configuration (Supabase Postgres, async via asyncpg)
# =============================================================================

import re
import ssl
import logging
from uuid import uuid4
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

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

    # Encrypt without verifying the cert chain (Supabase's chain isn't
    # always in the system trust store) -- equivalent to sslmode=require.
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # ── pgbouncer (transaction mode) + asyncpg prepared statements ──
    # Disabling the cache alone isn't enough: asyncpg names prepared
    # statements with a simple incrementing counter per connection
    # object. Since pgbouncer can route different logical connections
    # to the same physical backend, two connections can independently
    # generate the same statement name (e.g. "__asyncpg_stmt_5__") and
    # collide -> DuplicatePreparedStatementError, even on SQLAlchemy's
    # own internal setup queries like `select pg_catalog.version()`.
    # Fix: force globally-unique statement names via uuid4.
    connect_args = {
        "ssl": ssl_context,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    }

    return url, connect_args


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
    # NullPool: pgbouncer already pools connections. Letting SQLAlchemy
    # ALSO hold a pool on top creates double-pooling -- SQLAlchemy keeps
    # connections open/idle that pgbouncer then can't reassign to other
    # requests. NullPool opens a fresh connection per operation and lets
    # pgbouncer own the connection lifecycle, which is what SQLAlchemy's
    # own docs recommend behind a pooler like this.
    poolclass=NullPool,
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
