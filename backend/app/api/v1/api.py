from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth_router,
    users_router,
    categories_router,
    vehicles_router,
    mileage_router,
    valuations_router,
    payments_router,
    inspections_router,
    reports_router,
    settings_router
)

api_router = APIRouter()

# Include all endpoint routers with clean prefixes
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(users_router, prefix="/users")
api_router.include_router(categories_router, prefix="/categories")
api_router.include_router(vehicles_router, prefix="/vehicles")
api_router.include_router(mileage_router, prefix="/mileage")
api_router.include_router(valuations_router, prefix="/valuations")
api_router.include_router(payments_router, prefix="/payments")
api_router.include_router(inspections_router, prefix="/inspections")
api_router.include_router(reports_router, prefix="/reports")
api_router.include_router(settings_router, prefix="/settings")

# Root endpoint for v1
@api_router.get("/")
async def v1_root():
    return {"message": "AUTO-V API v1", "status": "running"}

__all__ = ["api_router"]
