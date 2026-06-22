# api/__init__.py - AUTO-V API Package
"""
AUTO-V API Routes Package
Contains all API route blueprints (Production Ready v2)
"""

import logging

logger = logging.getLogger(__name__)

# ─── Import All Blueprints Safely ──────────────────────────────

def safe_import(module_path, attr_name, label):
    """Safe dynamic import helper"""
    try:
        module = __import__(module_path, fromlist=[attr_name])
        blueprint = getattr(module, attr_name)
        logger.info(f"✅ {label} loaded")
        return blueprint
    except Exception as e:
        logger.warning(f"⚠️ {label} not available: {e}")
        return None


# ─── Core API Routes ───────────────────────────────────────────

admin_bp = safe_import(".routes.admin", "admin_bp", "Admin routes")
auth_bp = safe_import(".routes.auth", "auth_bp", "Auth routes")
inspections_bp = safe_import(".routes.inspections", "inspections_bp", "Inspection routes")
intelligence_bp = safe_import(".routes.intelligence", "intelligence_bp", "Intelligence routes")

# ─── Payment System (IMPORTANT ALIGNMENT AREA) ─────────────────

mpesa_bp = safe_import(".routes.mpesa", "mpesa_bp", "M-Pesa routes")
payments_bp = safe_import(".routes.payments", "payments_bp", "Payment routes")

# ─── Vehicle / Valuation / Services ────────────────────────────

valuations_bp = safe_import(".routes.valuations", "valuations_bp", "Valuation routes")
vehicles_bp = safe_import(".routes.vehicles", "vehicles_bp", "Vehicle routes")
services_bp = safe_import(".routes.services", "services_bp", "Service routes")

# ─── Assessment & Analytics ────────────────────────────────────

assessments_bp = safe_import(".routes.assessments", "assessments_bp", "Assessment routes")
mileage_bp = safe_import(".routes.mileage", "mileage_bp", "Mileage routes")

# ─── VIN System ────────────────────────────────────────────────

vin_router = safe_import(".routes.vin_routes", "router", "VIN routes")

# ─── Export All Blueprints ─────────────────────────────────────

__all__ = [
    'admin_bp',
    'auth_bp',
    'inspections_bp',
    'intelligence_bp',
    'mpesa_bp',
    'payments_bp',
    'valuations_bp',
    'vehicles_bp',
    'services_bp',
    'assessments_bp',
    'mileage_bp',
    'vin_router'
]

# ─── Blueprint Registration Helper ─────────────────────────────

def register_blueprints(app):
    """
    Register all available blueprints to Flask app.

    IMPORTANT ALIGNMENT NOTES:
    - M-Pesa routes must be under /api/mpesa
    - Payments routes must be under /api/payments
    - Supabase-backed tables MUST match:
        payments (NOT payment)
        mpesa fields mapped correctly

    Args:
        app: Flask application instance

    Returns:
        int: Number of successfully registered blueprints
    """

    blueprints = [
        (admin_bp, '/api/admin'),
        (auth_bp, '/api/auth'),
        (inspections_bp, '/api/inspections'),
        (intelligence_bp, '/api/intelligence'),

        # 💰 PAYMENT SYSTEM (CRITICAL)
        (mpesa_bp, '/api/mpesa'),
        (payments_bp, '/api/payments'),

        # 🚗 VEHICLE SYSTEM
        (valuations_bp, '/api/valuations'),
        (vehicles_bp, '/api/vehicles'),
        (services_bp, '/api/services'),

        # 📊 ANALYTICS / ASSESSMENTS
        (assessments_bp, '/api/assessments'),
        (mileage_bp, '/api/mileage'),

        # 🔎 VIN SYSTEM
        (vin_router, '/api/vin')
    ]

    registered_count = 0

    for blueprint, url_prefix in blueprints:
        if blueprint is None:
            continue

        try:
            app.register_blueprint(blueprint, url_prefix=url_prefix)
            registered_count += 1
            logger.info(f"✅ Registered: {blueprint.name} → {url_prefix}")

        except Exception as e:
            logger.error(f"❌ Failed to register {blueprint.name}: {e}")

    logger.info(f"📋 Blueprint registration complete: {registered_count}/{len(blueprints)}")
    return registered_count


# ─── Package Metadata ──────────────────────────────────────────

__version__ = "2.0.0"
__author__ = "AUTO-V Team"
__description__ = "AUTO-V API Routes Package (Production Ready v2)"
