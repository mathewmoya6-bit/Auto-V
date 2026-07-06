# backend/app/api/v1/api.py
# =============================================================================
# API Router - Register all endpoints
# =============================================================================

from fastapi import APIRouter

# ─── Import endpoint modules (only the ones that exist) ────────────────────
from app.api.v1.endpoints import (
    categories,
    valuations,
    inspections,
    mileage
)

# ─── Create API Router ──────────────────────────────────────────────────
api_router = APIRouter()

# ─── Categories ──────────────────────────────────────────────────────────
api_router.include_router(
    categories.router,
    prefix="/categories",
    tags=["categories"]
)

# ─── Valuations ──────────────────────────────────────────────────────
api_router.include_router(
    valuations.router,
    prefix="/valuations",
    tags=["valuations"]
)

# ─── Inspections ─────────────────────────────────────────────────────
api_router.include_router(
    inspections.router,
    prefix="/inspections",
    tags=["inspections"]
)

# ─── Mileage ─────────────────────────────────────────────────────────
api_router.include_router(
    mileage.router,
    prefix="/mileage",
    tags=["mileage"]
)

# ─── Health Check (Root level) ──────────────────────────────────────
@api_router.get("/health")
async def health_check():
    """API health check endpoint."""
    return {
        "status": "ok",
        "service": "AUTO-V API",
        "version": "3.1.0"
    }

@api_router.get("/")
async def api_root():
    """API root endpoint."""
    return {
        "service": "AUTO-V API",
        "version": "3.1.0",
        "docs": "/docs",
        "status": "running"
    }
