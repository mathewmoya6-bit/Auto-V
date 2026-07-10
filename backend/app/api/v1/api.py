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

router = APIRouter()

# Include all endpoint routers
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(users_router, prefix="/users", tags=["Users"])
router.include_router(categories_router, prefix="/categories", tags=["Categories"])
router.include_router(vehicles_router, prefix="/vehicles", tags=["Vehicles"])
router.include_router(mileage_router, prefix="/mileage", tags=["Mileage"])
router.include_router(valuation_router, prefix="/valuation", tags=["Valuation"])
router.include_router(payments_router, prefix="/payments", tags=["Payments"])
router.include_router(inspections_router, prefix="/inspections", tags=["Inspections"])
router.include_router(reports_router, prefix="/reports", tags=["Reports"])

# You can also add a root endpoint here if needed
@router.get("/")
async def root():
    return {"message": "AUTO-V API v1", "status": "running"}
