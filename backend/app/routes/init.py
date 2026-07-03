# backend/app/api/v1/routes/__init__.py
# =============================================================================
# AUTO-V API - Routes Package (v1)
# =============================================================================
# This file makes 'app.api.v1.routes' a Python package.
# It exports all route modules for easy import in main.py.
# =============================================================================

# ─── Core Routes ──────────────────────────────────────────────────────────
try:
    from app.api.v1.routes import auth
except ImportError:
    auth = None

try:
    from app.api.v1.routes import users
except ImportError:
    users = None

try:
    from app.api.v1.routes import vehicles
except ImportError:
    vehicles = None

try:
    from app.api.v1.routes import valuations
except ImportError:
    valuations = None

try:
    from app.api.v1.routes import payments
except ImportError:
    payments = None

try:
    from app.api.v1.routes import reports
except ImportError:
    reports = None

try:
    from app.api.v1.routes import webhooks
except ImportError:
    webhooks = None


# ─── Optional Routes ─────────────────────────────────────────────────────
try:
    from app.api.v1.routes import certificates
except ImportError:
    certificates = None

try:
    from app.api.v1.routes import mileage
except ImportError:
    mileage = None

try:
    from app.api.v1.routes import fleet
except ImportError:
    fleet = None

try:
    from app.api.v1.routes import admin
except ImportError:
    admin = None


# ─── Health Check Route ──────────────────────────────────────────────────
# The health check is typically defined in main.py, but can also be here
try:
    from app.api.v1.routes import health
except ImportError:
    health = None


# =============================================================================
# PUBLIC API - What gets exported
# =============================================================================

__all__ = [
    # Core routes
    "auth",
    "users",
    "vehicles",
    "valuations",
    "payments",
    "reports",
    "webhooks",
    # Optional routes
    "certificates",
    "mileage",
    "fleet",
    "admin",
    # Health
    "health",
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_available_routers() -> dict:
    """
    Get a dictionary of all successfully imported routers.
    
    Returns:
        dict: Router name to router module mapping
    """
    routers = {}
    
    # Core routers
    if auth is not None:
        routers["auth"] = auth
    if users is not None:
        routers["users"] = users
    if vehicles is not None:
        routers["vehicles"] = vehicles
    if valuations is not None:
        routers["valuations"] = valuations
    if payments is not None:
        routers["payments"] = payments
    if reports is not None:
        routers["reports"] = reports
    if webhooks is not None:
        routers["webhooks"] = webhooks
    
    # Optional routers
    if certificates is not None:
        routers["certificates"] = certificates
    if mileage is not None:
        routers["mileage"] = mileage
    if fleet is not None:
        routers["fleet"] = fleet
    if admin is not None:
        routers["admin"] = admin
    
    # Health
    if health is not None:
        routers["health"] = health
    
    return routers


def get_route_names() -> list:
    """
    Get list of all available route module names.
    
    Returns:
        list: Names of available route modules
    """
    return list(get_available_routers().keys())


def is_route_available(route_name: str) -> bool:
    """
    Check if a specific route module is available.
    
    Args:
        route_name: Name of the route module to check
        
    Returns:
        bool: True if the route is available, False otherwise
    """
    return route_name in get_available_routers()


# =============================================================================
# LOGGING
# =============================================================================

import logging

logger = logging.getLogger(__name__)

# Log available routes on import
available = get_available_routers()
logger.info(f"📦 Available routes: {', '.join(available.keys())}")

if not available:
    logger.warning("⚠️  No route modules found! Make sure route files exist.")
