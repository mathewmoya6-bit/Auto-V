# app/api/v1/api.py
# =============================================================================
# AUTO-V API - API Router Aggregator
# =============================================================================

import logging
from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    mileage,
    vehicles,
    valuation,
    inspections,
    fleets,
    certificates,
    payments,
    dashboard,
)

logger = logging.getLogger(__name__)

api_router = APIRouter()

# ─── Register all route groups ──────────────────────────────────────

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(mileage.router, prefix="/mileage", tags=["Mileage"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles"])
api_router.include_router(valuation.router, prefix="/valuations", tags=["Valuations"])
api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections"])
api_router.include_router(fleets.router, prefix="/fleets", tags=["Fleets"])
api_router.include_router(certificates.router, prefix="/certificates", tags=["Certificates"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])


# ─── System Endpoints ──────────────────────────────────────────────

@api_router.get("/ping", tags=["System"])
async def ping():
    return {
        "status": "ok",
        "message": "AUTO-V API is running",
        "version": "3.1.0"
    }


logger.info("✅ All routes registered successfully")
