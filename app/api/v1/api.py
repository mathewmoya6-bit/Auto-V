# app/api/v1/api.py
# =============================================================================
# AUTO-V API - V1 Router Assembly
# =============================================================================
from fastapi import APIRouter

from app.api.v1.routes import auth, vehicles, valuations, mileage, inspections

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(vehicles.router)
api_router.include_router(valuations.router)
api_router.include_router(mileage.router)
api_router.include_router(inspections.router)
