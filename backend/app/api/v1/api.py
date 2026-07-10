from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, categories, vehicles, mileage, 
    valuation, payments, inspections, reports
)

router = APIRouter(prefix="/api/v1")

# Include all endpoint routers
router.include_router(auth.router, tags=["Authentication"])
router.include_router(users.router, tags=["Users"])
router.include_router(categories.router, tags=["Categories"])
router.include_router(vehicles.router, tags=["Vehicles"])
router.include_router(mileage.router, tags=["Mileage"])
router.include_router(valuation.router, tags=["Valuation"])
router.include_router(payments.router, tags=["Payments"])
router.include_router(inspections.router, tags=["Inspections"])
router.include_router(reports.router, tags=["Reports"])
