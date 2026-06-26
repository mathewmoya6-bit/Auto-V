"""
Routes Package - All API Routes
"""

from app.routes import (
    health,
    auth,
    mpesa,
    valuation,
    valuations,
    certificates,
    vehicles,
    dashboard,
    vin,
    vin_routes,
    webhooks,
    admin,
    assessments,
    inspection,
    intelligence,
    payments,
    services,
    fuel
)

__all__ = [
    "health",
    "auth",
    "mpesa",
    "valuation",
    "valuations",
    "certificates",
    "vehicles",
    "dashboard",
    "vin",
    "vin_routes",
    "webhooks",
    "admin",
    "assessments",
    "inspection",
    "intelligence",
    "payments",
    "services",
    "fuel"
]
