# app/api/v1/api.py
# =============================================================================
# AUTO-V API - API Router Aggregator (Version 1)
# =============================================================================

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional

from app.core.database import is_configured
from app.api.v1.routes import (
    auth,
    mileage,
    vehicles,
    valuations,
    inspections,
    certificates,
    payments,
    fleets,
    dashboard,
    admin,
    webhooks,
    reports,
    settings as settings_routes,
)

logger = logging.getLogger(__name__)

# ─── Main Router ──────────────────────────────────────────────────────

api_router = APIRouter()


# ─── Health & System Endpoints ──────────────────────────────────────

@api_router.get("/ping", tags=["System"])
async def ping():
    """
    Ping endpoint to verify API is running.
    
    Returns:
        Simple status response
    """
    return {
        "status": "ok",
        "message": "AUTO-V API is running",
        "version": "3.1.0",
        "timestamp": "2026-07-07T00:00:00Z"
    }


@api_router.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Detailed health status including database connectivity
    """
    return {
        "status": "healthy" if is_configured() else "degraded",
        "service": "AUTO-V API",
        "version": "3.1.0",
        "database": {
            "configured": is_configured(),
            "connected": is_configured()  # Will be enhanced with actual connection check
        },
        "timestamp": "2026-07-07T00:00:00Z"
    }


@api_router.get("/version", tags=["System"])
async def get_version():
    """
    Get API version information.
    """
    return {
        "version": "3.1.0",
        "release_date": "2026-07-07",
        "api_prefix": "/api/v1",
        "documentation": "/docs",
        "status": "stable"
    }


# ─── Authentication Routes ──────────────────────────────────────────

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)


# ─── Vehicle Management Routes ──────────────────────────────────────

api_router.include_router(
    vehicles.router,
    prefix="/vehicles",
    tags=["Vehicles"]
)

api_router.include_router(
    vehicles.vin_router,
    prefix="/vehicles/vin",
    tags=["VIN Scanning"]
)

api_router.include_router(
    vehicles.image_router,
    prefix="/vehicles/images",
    tags=["Vehicle Images"]
)


# ─── Valuation Routes ──────────────────────────────────────────────

api_router.include_router(
    valuations.router,
    prefix="/valuations",
    tags=["Valuations"]
)

api_router.include_router(
    valuations.instant_router,
    prefix="/valuations/instant",
    tags=["Instant Value"]
)

api_router.include_router(
    valuations.bulk_router,
    prefix="/valuations/bulk",
    tags=["Bulk Valuations"]
)

api_router.include_router(
    valuations.history_router,
    prefix="/valuations/history",
    tags=["Valuation History"]
)


# ─── Inspection Routes ──────────────────────────────────────────────

api_router.include_router(
    inspections.router,
    prefix="/inspections",
    tags=["Inspections"]
)

api_router.include_router(
    inspections.checklist_router,
    prefix="/inspections/checklists",
    tags=["Inspection Checklists"]
)

api_router.include_router(
    inspections.report_router,
    prefix="/inspections/reports",
    tags=["Inspection Reports"]
)


# ─── Mileage & Running Cost Routes ──────────────────────────────────

api_router.include_router(
    mileage.router,
    prefix="/mileage",
    tags=["Mileage"]
)

api_router.include_router(
    mileage.categories_router,
    prefix="/mileage/categories",
    tags=["Vehicle Categories"]
)

api_router.include_router(
    mileage.variants_router,
    prefix="/mileage/variants",
    tags=["Vehicle Variants"]
)

api_router.include_router(
    mileage.routes_router,
    prefix="/mileage/routes",
    tags=["Routes"]
)

api_router.include_router(
    mileage.claims_router,
    prefix="/mileage/claims",
    tags=["Mileage Claims"]
)

api_router.include_router(
    mileage.rates_router,
    prefix="/mileage/rates",
    tags=["Running Cost Rates"]
)

api_router.include_router(
    mileage.calculate_router,
    prefix="/mileage/calculate",
    tags=["Cost Calculation"]
)


# ─── Fleet Management Routes ────────────────────────────────────────

api_router.include_router(
    fleets.router,
    prefix="/fleets",
    tags=["Fleets"]
)

api_router.include_router(
    fleets.vehicles_router,
    prefix="/fleets/vehicles",
    tags=["Fleet Vehicles"]
)

api_router.include_router(
    fleets.drivers_router,
    prefix="/fleets/drivers",
    tags=["Fleet Drivers"]
)

api_router.include_router(
    fleets.analytics_router,
    prefix="/fleets/analytics",
    tags=["Fleet Analytics"]
)


# ─── Certificate Routes ─────────────────────────────────────────────

api_router.include_router(
    certificates.router,
    prefix="/certificates",
    tags=["Certificates"]
)

api_router.include_router(
    certificates.verify_router,
    prefix="/certificates/verify",
    tags=["Certificate Verification"]
)

api_router.include_router(
    certificates.qr_router,
    prefix="/certificates/qr",
    tags=["QR Codes"]
)


# ─── Payment Routes ──────────────────────────────────────────────────

api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["Payments"]
)

api_router.include_router(
    payments.mpesa_router,
    prefix="/payments/mpesa",
    tags=["M-Pesa Payments"]
)

api_router.include_router(
    payments.webhook_router,
    prefix="/payments/webhooks",
    tags=["Payment Webhooks"]
)


# ─── Dashboard & Analytics Routes ──────────────────────────────────

api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"]
)

api_router.include_router(
    dashboard.metrics_router,
    prefix="/dashboard/metrics",
    tags=["Metrics"]
)

api_router.include_router(
    dashboard.activity_router,
    prefix="/dashboard/activity",
    tags=["Activity"]
)


# ─── Report Routes ──────────────────────────────────────────────────

api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"]
)

api_router.include_router(
    reports.export_router,
    prefix="/reports/export",
    tags=["Report Export"]
)

api_router.include_router(
    reports.scheduled_router,
    prefix="/reports/scheduled",
    tags=["Scheduled Reports"]
)


# ─── Admin Routes ────────────────────────────────────────────────────

api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"]
)

api_router.include_router(
    admin.users_router,
    prefix="/admin/users",
    tags=["Admin Users"]
)

api_router.include_router(
    admin.settings_router,
    prefix="/admin/settings",
    tags=["Admin Settings"]
)

api_router.include_router(
    admin.audit_router,
    prefix="/admin/audit",
    tags=["Audit Logs"]
)

api_router.include_router(
    admin.rates_router,
    prefix="/admin/rates",
    tags=["Admin Rates"]
)


# ─── Webhook Routes ──────────────────────────────────────────────────

api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["Webhooks"]
)


# ─── Settings Routes ─────────────────────────────────────────────────

api_router.include_router(
    settings_routes.router,
    prefix="/settings",
    tags=["Settings"]
)


# ─── Error Handlers ──────────────────────────────────────────────────

@api_router.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom HTTP exception handler.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path
        }
    )


@api_router.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "detail": "An internal server error occurred",
            "path": request.url.path
        }
    )


# ─── Logging Middleware ─────────────────────────────────────────────

@api_router.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests.
    """
    import time
    
    start_time = time.time()
    
    # Log request
    logger.info(
        f"➡️ {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown"
        }
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"⬅️ {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration": round(process_time, 3)
        }
    )
    
    return response


# ─── Module Logger ──────────────────────────────────────────────────

logger.info("✅ All routes registered successfully")
logger.info(f"📋 Total route groups: {len(api_router.routes)}")
