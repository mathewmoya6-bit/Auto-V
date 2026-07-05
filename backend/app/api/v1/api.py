# # app/api/v1/api.py
# =============================================================================
# AUTO-V API - v1 router aggregator
# =============================================================================

from fastapi import APIRouter

from app.api.v1.endpoints import categories, routes, vehicles

api_router = APIRouter()
api_router.include_router(categories.router, tags=["categories"])
api_router.include_router(vehicles.router, tags=["vehicles"])
api_router.include_router(routes.router, tags=["routes"])
# =============================================================================
# AUTO-V API - v1 router aggregator
# =============================================================================

from fastapi import APIRouter

from app.api.v1.endpoints import categories, routes, vehicles

api_router = APIRouter()
api_router.include_router(categories.router, tags=["categories"])
api_router.include_router(vehicles.router, tags=["vehicles"])
api_router.include_router(routes.router, tags=["routes"])
