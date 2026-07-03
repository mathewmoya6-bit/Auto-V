# app/core/database.py
# Inferred from init_db()/close_db() usage in main.py's lifespan.
# Uses SQLAlchemy's async engine (requires the `asyncpg` driver —
# DATABASE_URL must use `postgresql+asyncpg://`).
#
# ⚠️ IMPORTANT — read before relying on init_db() in production:
# init_db() below calls Base.metadata.create_all(), which will
# CREATE any table defined in app/models.py that doesn't already
# exist in the database. Your Supabase project already has these
# tables created via hand-written SQL (with RLS policies) run
# directly in the Supabase SQL editor. If this backend's
# create_all() runs against THAT SAME database, it will try to
# create tables that already exist — SQLAlchemy's create_all() is
# safe here (it checks existence first and won't clobber existing
# tables/data), but it also won't apply this app's differing column
# definitions (e.g. Certificate.metadata vs the Supabase version's
# columns) to already-existing tables, and it does NOT create RLS
# policies at all — those only exist because you ran the SQL editor
# scripts separately. In short: two schema sources of truth right
# now. Worth deciding which one (hand-written Supabase SQL, or this
# SQLAlchemy models.py) actually owns table creation going forward,
# rather than running both.

import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models import Base  # adjust if models becomes a package — see note in chat

logger = logging.getLogger("app")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create any tables defined in models.py that don't already exist.
    See the module-level note above about this potentially overlapping
    with tables already created via the Supabase SQL editor."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified/created")


async def close_db() -> None:
    await engine.dispose()


async def get_db():
    """FastAPI dependency — yields an AsyncSession per request.

    Usage in a route:
        from app.core.database import get_db
        from fastapi import Depends

        @router.get("/vehicles")
        async def list_vehicles(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
