# app/api/v1/api.py
# =============================================================================
# AUTO-V API - API Router Aggregator
# =============================================================================

from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    mileage,
    vehicles,
    valuations,
    inspections,
    fleets,
    certificates,
    payments,
    dashboard,
    reports,
    admin,
    webhooks
)

# Create main API router
api_router = APIRouter()

# ─── Authentication ──────────────────────────────────────────────────
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# ─── Vehicle Management ─────────────────────────────────────────────
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles"])
api_router.include_router(vehicles.vin_router, prefix="/vehicles", tags=["VIN Scanning"])
api_router.include_router(vehicles.image_router, prefix="/vehicles", tags=["Vehicle Images"])

# ─── Valuations ─────────────────────────────────────────────────────
api_router.include_router(valuations.router, prefix="/valuations", tags=["Valuations"])
api_router.include_router(valuations.instant_router, prefix="/valuations", tags=["Instant Value"])
api_router.include_router(valuations.bulk_router, prefix="/valuations", tags=["Bulk Valuations"])
api_router.include_router(valuations.history_router, prefix="/valuations", tags=["Valuation History"])

# ─── Inspections ────────────────────────────────────────────────────
api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections"])
api_router.include_router(inspections.checklist_router, prefix="/inspections", tags=["Inspection Checklists"])
api_router.include_router(inspections.report_router, prefix="/inspections", tags=["Inspection Reports"])

# ─── Mileage & Running Costs ────────────────────────────────────────
api_router.include_router(mileage.router, prefix="/mileage", tags=["Mileage"])
api_router.include_router(mileage.categories_router, prefix="/mileage", tags=["Vehicle Categories"])
api_router.include_router(mileage.variants_router, prefix="/mileage", tags=["Vehicle Variants"])
api_router.include_router(mileage.routes_router, prefix="/mileage", tags=["Routes"])
api_router.include_router(mileage.claims_router, prefix="/mileage", tags=["Mileage Claims"])
api_router.include_router(mileage.rates_router, prefix="/mileage", tags=["Running Cost Rates"])
api_router.include_router(mileage.calculate_router, prefix="/mileage", tags=["Cost Calculation"])

# ─── Fleet Management ──────────────────────────────────────────────
api_router.include_router(fleets.router, prefix="/fleets", tags=["Fleets"])
api_router.include_router(fleets.vehicles_router, prefix="/fleets", tags=["Fleet Vehicles"])
api_router.include_router(fleets.drivers_router, prefix="/fleets", tags=["Fleet Drivers"])
api_router.include_router(fleets.analytics_router, prefix="/fleets", tags=["Fleet Analytics"])

# ─── Certificates ───────────────────────────────────────────────────
api_router.include_router(certificates.router, prefix="/certificates", tags=["Certificates"])
api_router.include_router(certificates.verify_router, prefix="/certificates", tags=["Certificate Verification"])
api_router.include_router(certificates.qr_router, prefix="/certificates", tags=["QR Codes"])

# ─── Payments ──────────────────────────────────────────────────────
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(payments.mpesa_router, prefix="/payments", tags=["M-Pesa"])
api_router.include_router(payments.webhook_router, prefix="/payments", tags=["Payment Webhooks"])

# ─── Dashboard & Analytics ─────────────────────────────────────────
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(dashboard.metrics_router, prefix="/dashboard", tags=["Metrics"])
api_router.include_router(dashboard.activity_router, prefix="/dashboard", tags=["Activity"])

# ─── Reports ──────────────────────────────────────────────────────
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(reports.export_router, prefix="/reports", tags=["Report Export"])
api_router.include_router(reports.scheduled_router, prefix="/reports", tags=["Scheduled Reports"])

# ─── Admin ─────────────────────────────────────────────────────────
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin.users_router, prefix="/admin", tags=["Admin Users"])
api_router.include_router(admin.settings_router, prefix="/admin", tags=["Admin Settings"])
api_router.include_router(admin.audit_router, prefix="/admin", tags=["Audit Logs"])
api_router.include_router(admin.rates_router, prefix="/admin", tags=["Admin Rates"])

# ─── Webhooks ──────────────────────────────────────────────────────
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])


# ─── Health & Ping Endpoints ──────────────────────────────────────

@api_router.get("/ping")
async def api_ping():
    """Ping endpoint to verify API is running"""
    return {
        "status": "ok",
        "message": "AUTO-V API is running",
        "version": "3.1.0",
        "services": [
            "Authentication",
            "Vehicles",
            "Valuations",
            "Inspections",
            "Mileage",
            "Fleets",
            "Certificates",
            "Payments",
            "Dashboard",
            "Reports",
            "Admin",
            "Webhooks"
        ]
    }


@api_router.get("/health")
async def api_health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AUTO-V API",
        "version": "3.1.0",
        "timestamp": "2026-07-07T12:00:00Z"
    }


@api_router.get("/version")
async def api_version():
    """Get API version"""
    return {
        "version": "3.1.0",
        "release_date": "2026-07-07",
        "changelog": "https://auto-v.africa/changelog"
    }
