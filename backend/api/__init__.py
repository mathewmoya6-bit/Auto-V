# api/__init__.py - AUTO-V API Package
"""
AUTO-V API Routes Package
Contains all API route blueprints
"""

import logging

logger = logging.getLogger(__name__)

# ─── Import All Blueprints ──────────────────────────────────────

try:
    from .routes.admin import admin_bp
    logger.info("✅ Admin routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Admin routes not available: {e}")
    admin_bp = None

try:
    from .routes.auth import auth_bp
    logger.info("✅ Auth routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Auth routes not available: {e}")
    auth_bp = None

try:
    from .routes.inspections import inspections_bp
    logger.info("✅ Inspection routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Inspection routes not available: {e}")
    inspections_bp = None

try:
    from .routes.intelligence import intelligence_bp
    logger.info("✅ Intelligence routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Intelligence routes not available: {e}")
    intelligence_bp = None

try:
    from .routes.mpesa import mpesa_bp
    logger.info("✅ M-Pesa routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ M-Pesa routes not available: {e}")
    mpesa_bp = None

try:
    from .routes.payments import payments_bp
    logger.info("✅ Payment routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Payment routes not available: {e}")
    payments_bp = None

try:
    from .routes.valuations import valuations_bp
    logger.info("✅ Valuation routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Valuation routes not available: {e}")
    valuations_bp = None

try:
    from .routes.vehicles import vehicles_bp
    logger.info("✅ Vehicle routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Vehicle routes not available: {e}")
    vehicles_bp = None

try:
    from .routes.services import services_bp
    logger.info("✅ Service routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Service routes not available: {e}")
    services_bp = None

try:
    from .routes.assessments import assessments_bp
    logger.info("✅ Assessment routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Assessment routes not available: {e}")
    assessments_bp = None

try:
    from .routes.mileage import mileage_bp
    logger.info("✅ Mileage routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Mileage routes not available: {e}")
    mileage_bp = None

try:
    from .routes.vin_routes import router as vin_router
    logger.info("✅ VIN routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ VIN routes not available: {e}")
    vin_router = None

# ─── Export All Blueprints ──────────────────────────────────────

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

# ─── Register Blueprints Helper ────────────────────────────────

def register_blueprints(app):
    """
    Register all blueprints to the Flask app.
    
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
        (mpesa_bp, '/api/mpesa'),
        (payments_bp, '/api/payments'),
        (valuations_bp, '/api/valuations'),
        (vehicles_bp, '/api/vehicles'),
        (services_bp, '/api/services'),
        (assessments_bp, '/api/assessments'),
        (mileage_bp, '/api/mileage'),
        (vin_router, '/api/vin')
    ]
    
    registered_count = 0
    for blueprint, url_prefix in blueprints:
        if blueprint is not None:
            try:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
                registered_count += 1
                logger.info(f"✅ Registered: {blueprint.name} at {url_prefix}")
            except Exception as e:
                logger.error(f"❌ Failed to register {blueprint.name}: {e}")
    
    logger.info(f"📋 Registered {registered_count}/{len(blueprints)} blueprints")
    return registered_count

# ─── Package Info ────────────────────────────────────────────────

__version__ = '1.0.0'
__author__ = 'AUTO-V Team'
__description__ = 'AUTO-V API Routes Package'
