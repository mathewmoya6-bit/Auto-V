"""
API Router - Register all endpoints
"""

from fastapi import APIRouter

# Import only the endpoint modules that exist
from app.api.v1.endpoints import (
    categories,
    valuations,
    inspections,
    mileage
)

api_router = APIRouter()

# Register all routers
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(valuations.router, prefix="/valuations", tags=["valuations"])
api_router.include_router(inspections.router, prefix="/inspections", tags=["inspections"])
api_router.include_router(mileage.router, prefix="/mileage", tags=["mileage"])

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "ok", "service": "AUTO-V API", "version": "3.1.0"}

@api_router.get("/")
async def api_root():
    return {"service": "AUTO-V API", "version": "3.1.0", "docs": "/docs", "status": "running"}
