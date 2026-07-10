# app/api/v1/api.py
# =============================================================================
# AUTO-V API - v1 Router Aggregator
# =============================================================================
"""
Combines all v1 endpoint routers into one. main.py mounts this at
settings.api_v1_prefix ("/api/v1"), so routes here become e.g.
/api/v1/auth/login.

If you already have other routers (vehicles, users, valuations, etc.)
registered here, keep them — just make sure the `auth` import and
`include_router` line below are present alongside them.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# ─── Add your other routers below, e.g.: ──────────────────────────────────
# from app.api.v1.endpoints import vehicles, users, valuations
# api_router.include_router(vehicles.router, prefix="/vehicles", tags=["vehicles"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(valuations.router, prefix="/valuations", tags=["valuations"])
