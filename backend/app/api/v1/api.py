# app/api/v1/api.py
# =============================================================================
# AUTO-V API - API Router Aggregator
# =============================================================================

from fastapi import APIRouter

# Import routes directly, not from __init__
from app.api.v1.routes import auth
from app.api.v1.routes import mileage

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(mileage.router, prefix="/mileage", tags=["Mileage"])

# Uncomment as you add more routes
# from app.api.v1.routes import vehicles
# api_router.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles"])


@api_router.get("/ping")
async def api_ping():
    """Ping endpoint to verify API is running"""
    return {
        "status": "ok",
        "message": "AUTO-V API is running",
        "version": "3.1.0"
    }
