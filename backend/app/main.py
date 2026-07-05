# app/main.py
# =============================================================================
# AUTO-V API - FastAPI entrypoint
# =============================================================================

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import check_db_health, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are managed via mileage_schema.sql / migrations, not created here.
    yield
    await close_db()


app = FastAPI(
    title="AUTO-V API",
    version="3.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"service": "AUTO-V API", "version": "3.1.0", "docs": "/docs"}


@app.get("/health")
async def health():
    db_ok = await check_db_health()
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
