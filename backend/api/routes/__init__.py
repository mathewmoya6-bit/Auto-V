"""
Routes Package
"""

from app.routes import health, auth, mpesa, valuation, certificates, vehicles, dashboard, vin, webhooks

__all__ = [
    "health",
    "auth",
    "mpesa",
    "valuation",
    "certificates",
    "vehicles",
    "dashboard",
    "vin",
    "webhooks"
]
