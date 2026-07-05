# backend/app/api/v1/api.py
# =============================================================================
# API Router - Register all endpoints
# =============================================================================

from fastapi import APIRouter

# ─── Import all endpoint modules ──────────────────────────────────────────
from app.api.v1.endpoints import (
    auth,                    # Authentication endpoints
    users,                   # User management endpoints
    profiles,                # User profile endpoints
    categories,              # Vehicle categories endpoints
    vehicles,                # Vehicle management endpoints
    variants,                # Vehicle variants endpoints
    routes,                  # Routes management endpoints
    calculate,               # Mileage calculation endpoints
    valuations,              # Vehicle valuation endpoints
    inspections,             # Vehicle inspection endpoints
    assessments,             # Vehicle assessment endpoints
    service_requests,        # Service request endpoints
    payments,                # Payment processing endpoints
    certificates,            # Certificate management endpoints
    reports,                 # Report generation endpoints
    settings,                # Application settings endpoints
    admin,                   # Admin management endpoints
    dashboard,               # Dashboard data endpoints
    fuel,                    # Fuel price management endpoints
    mileage,                 # Mileage claim endpoints
    fleet                    # Fleet management endpoints
)

# ─── Create API Router ──────────────────────────────────────────────────
api_router = APIRouter()

# ─── Authentication (No prefix) ──────────────────────────────────────
api_router.include_router(
    auth.router,
    tags=["authentication"]
)

# ─── User Management ──────────────────────────────────────────────────
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    profiles.router,
    prefix="/profiles",
    tags=["profiles"]
)

# ─── Vehicle Management ──────────────────────────────────────────────
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
    variants.router,
    prefix="/variants",
    tags=["variants"]
)

# ─── Routes ──────────────────────────────────────────────────────────
api_router.include_router(
    routes.router,
    prefix="/routes",
    tags=["routes"]
)

# ─── Calculations ────────────────────────────────────────────────────
api_router.include_router(
    calculate.router,
    prefix="/calculate",
    tags=["calculations"]
)

# ─── Valuations ──────────────────────────────────────────────────────
api_router.include_router(
    valuations.router,
    prefix="/valuations",
    tags=["valuations"]
)

# ─── Inspections ─────────────────────────────────────────────────────
api_router.include_router(
    inspections.router,
    prefix="/inspections",
    tags=["inspections"]
)

# ─── Assessments ─────────────────────────────────────────────────────
api_router.include_router(
    assessments.router,
    prefix="/assessments",
    tags=["assessments"]
)

# ─── Service Requests ────────────────────────────────────────────────
api_router.include_router(
    service_requests.router,
    prefix="/service-requests",
    tags=["service-requests"]
)

# ─── Payments ────────────────────────────────────────────────────────
api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["payments"]
)

# ─── Certificates ────────────────────────────────────────────────────
api_router.include_router(
    certificates.router,
    prefix="/certificates",
    tags=["certificates"]
)

# ─── Reports ─────────────────────────────────────────────────────────
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["reports"]
)

# ─── Settings ────────────────────────────────────────────────────────
api_router.include_router(
    settings.router,
    prefix="/settings",
    tags=["settings"]
)

# ─── Admin ───────────────────────────────────────────────────────────
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"]
)

# ─── Dashboard ───────────────────────────────────────────────────────
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"]
)

# ─── Fuel ────────────────────────────────────────────────────────────
api_router.include_router(
    fuel.router,
    prefix="/fuel",
    tags=["fuel"]
)

# ─── Mileage ─────────────────────────────────────────────────────────
api_router.include_router(
    mileage.router,
    prefix="/mileage",
    tags=["mileage"]
)

# ─── Fleet ───────────────────────────────────────────────────────────
api_router.include_router(
    fleet.router,
    prefix="/fleet",
    tags=["fleet"]
)

# ─── Health Check (Root level) ──────────────────────────────────────
@api_router.get("/health")
async def health_check():
    """API health check endpoint."""
    return {
        "status": "ok",
        "service": "AUTO-V API",
        "version": "3.1.0"
    }

@api_router.get("/")
async def api_root():
    """API root endpoint."""
    return {
        "service": "AUTO-V API",
        "version": "3.1.0",
        "docs": "/docs",
        "status": "running"
    }
