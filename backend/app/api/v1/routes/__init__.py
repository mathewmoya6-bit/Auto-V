# app/api/v1/routes/__init__.py

from app.api.v1.routes import auth
from app.api.v1.routes import users
from app.api.v1.routes import vehicles
from app.api.v1.routes import valuations
from app.api.v1.routes import payments
from app.api.v1.routes import reports
from app.api.v1.routes import webhooks
from app.api.v1.routes import mileage  # ✅ Add this
from app.api.v1.routes import certificates
from app.api.v1.routes import fleet
from app.api.v1.routes import admin

__all__ = [
    "auth",
    "users",
    "vehicles",
    "valuations",
    "payments",
    "reports",
    "webhooks",
    "mileage",
    "certificates",
    "fleet",
    "admin",
]
