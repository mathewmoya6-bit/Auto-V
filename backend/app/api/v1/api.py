from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth_router,
    users_router,
    categories_router,
    vehicles_router,
    mileage_router,
    instant_value_router,
    vehicle_assessments_router,
    valuations_router,
    payments_router,
    inspections_router,
    reports_router,
    settings_router
)

api_router = APIRouter()

# Include all endpoint routers with clean prefixes
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(categories_router, prefix="/categories", tags=["Categories"])
api_router.include_router(vehicles_router, prefix="/vehicles", tags=["Vehicles"])
api_router.include_router(mileage_router, prefix="/mileage", tags=["Mileage"])
api_router.include_router(instant_value_router, prefix="/instant-value", tags=["Instant Value"])
api_router.include_router(vehicle_assessments_router, prefix="/vehicle-assessments", tags=["Vehicle Assessments"])
api_router.include_router(valuations_router, prefix="/valuations", tags=["Valuations"])
api_router.include_router(payments_router, prefix="/payments", tags=["Payments"])
api_router.include_router(inspections_router, prefix="/inspections", tags=["Inspections"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
api_router.include_router(settings_router, prefix="/settings", tags=["Settings"])

@api_router.get("/", tags=["Root"])
async def v1_root():
    return {"message": "AUTO-V API v1", "status": "running", "version": "1.0.0"}

__all__ = ["api_router"]
