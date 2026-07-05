# backend/app/api/v1/api.py
# ============================================================
# API Router - Register all endpoints
# ============================================================

from fastapi import APIRouter
from app.api.v1.endpoints import categories, vehicles, routes, calculate

api_router = APIRouter()

api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["vehicles"])
api_router.include_router(routes.router, prefix="/routes", tags=["routes"])
api_router.include_router(calculate.router, tags=["calculations"])  # Add this line
