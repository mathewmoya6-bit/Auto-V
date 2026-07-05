# backend/app/api/v1/api.py
# =============================================================================
# API Router - Register all endpoints
# =============================================================================

from fastapi import APIRouter
from app.api.v1.endpoints import auth, categories, vehicles, routes, calculate
from app.api.v1.endpoints import valuations, inspections

api_router = APIRouter()

# Register all endpoint routers
api_router.include_router(
    auth.router,
    tags=["authentication"]
)
api_router.include_router(
    categories.router,
    prefix="/categories",
    tags=["categories"]
)
api_router.include_router(
    vehicles.router,
    prefix="/vehicles",
    tags=["vehicles"]
)
api_router.include_router(
    routes.router,
    prefix="/routes",
    tags=["routes"]
)
api_router.include_router(
    calculate.router,
    tags=["calculations"]
)
api_router.include_router(
    valuations.router,
    tags=["valuations"]
)
api_router.include_router(
    inspections.router,
    tags=["inspections"]
)
