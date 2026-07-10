from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth_router,
    users_router,
    categories_router,
    vehicles_router,
    mileage_router,
    valuation_router,
    payments_router,
    inspections_router,
    reports_router
)

# Name it api_router to match main.py import
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(categories_router, prefix="/categories", tags=["Categories"])
api_router.include_router(vehicles_router, prefix="/vehicles", tags=["Vehicles"])
api_router.include_router(mileage_router, prefix="/mileage", tags=["Mileage"])
api_router.include_router(valuation_router, prefix="/valuation", tags=["Valuation"])
api_router.include_router(payments_router, prefix="/payments", tags=["Payments"])
api_router.include_router(inspections_router, prefix="/inspections", tags=["Inspections"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])

# Root endpoint for v1
@api_router.get("/")
async def v1_root():
    return {"message": "AUTO-V API v1", "status": "running"}

# Export api_router directly
__all__ = ["api_router"]
