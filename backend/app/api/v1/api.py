# backend/app/api/v1/api.py
# ============================================================
# API Router - Register all endpoints
# ============================================================

from fastapi import APIRouter
from app.api.v1.endpoints import categories, vehicles, routes, calculate

api_router = APIRouter()

# Register all endpoint routers
api_router.include_router(
    categories.router,
    prefix="/categories",
    tags=["categories"]
)
api_router.include_router(
    vehicles.router,
    prefix="/vehicles",
    tags=["vehicles"]
)
api_router.include_router(
    routes.router,
    prefix="/routes",
    tags=["routes"]
)
api_router.include_router(
    calculate.router,
    tags=["calculations"]  # This registers /calculate/mileage
)

# ============================================================
# Health endpoints at root level
# ============================================================

@api_router.get("/health")
async def api_health():
    """API health check."""
    return {"status": "ok", "service": "AUTO-V API"}

@api_router.get("/")
async def api_root():
    """API root."""
    return {"service": "AUTO-V API", "version": "3.1.0"}
