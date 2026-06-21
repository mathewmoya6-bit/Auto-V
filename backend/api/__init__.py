# api/__init__.py - AUTO-V API Routes Package
# This file imports and exports all route blueprints

import logging
from flask import Blueprint

logger = logging.getLogger(__name__)

# ─── Import All Blueprints ──────────────────────────────────────

try:
    from .routes.vin_routes import router as vin_router
    logger.info("✅ VIN routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ VIN routes not available: {e}")
    vin_router = None

try:
    from .routes.mpesa import mpesa_bp
    logger.info("✅ M-Pesa routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ M-Pesa routes not available: {e}")
    mpesa_bp = None

try:
    from .routes.auth import auth_bp
    logger.info("✅ Auth routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Auth routes not available: {e}")
    auth_bp = None

try:
    from .routes.vehicles import vehicles_bp
    logger.info("✅ Vehicle routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Vehicle routes not available: {e}")
    vehicles_bp = None

try:
    from .routes.valuations import valuations_bp
    logger.info("✅ Valuation routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Valuation routes not available: {e}")
    valuations_bp = None

try:
    from .routes.inspections import inspections_bp
    logger.info("✅ Inspection routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Inspection routes not available: {e}")
    inspections_bp = None

try:
    from .routes.admin import admin_bp
    logger.info("✅ Admin routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Admin routes not available: {e}")
    admin_bp = None

try:
    from .routes.services import services_bp
    logger.info("✅ Service routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Service routes not available: {e}")
    services_bp = None

try:
    from .routes.payments import payments_bp
    logger.info("✅ Payment routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Payment routes not available: {e}")
    payments_bp = None

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
    from .routes.intelligence import intelligence_bp
    logger.info("✅ Intelligence routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Intelligence routes not available: {e}")
    intelligence_bp = None

# ─── Export All Blueprints ──────────────────────────────────────

__all__ = [
    'vin_router',
    'mpesa_bp',
    'auth_bp',
    'vehicles_bp',
    'valuations_bp',
    'inspections_bp',
    'admin_bp',
    'services_bp',
    'payments_bp',
    'assessments_bp',
    'mileage_bp',
    'intelligence_bp'
]

# ─── Register Blueprints Helper ────────────────────────────────

def register_blueprints(app):
    """
    Register all blueprints to the Flask app.
    
    Args:
        app: Flask application instance
    """
    blueprints = [
        (vin_router, '/api/vin'),
        (mpesa_bp, '/api/mpesa'),
        (auth_bp, '/api/auth'),
        (vehicles_bp, '/api/vehicles'),
        (valuations_bp, '/api/valuations'),
        (inspections_bp, '/api/inspections'),
        (admin_bp, '/api/admin'),
        (services_bp, '/api/services'),
        (payments_bp, '/api/payments'),
        (assessments_bp, '/api/assessments'),
        (mileage_bp, '/api/mileage'),
        (intelligence_bp, '/api/intelligence')
    ]
    
    registered_count = 0
    for blueprint, url_prefix in blueprints:
        if blueprint is not None:
            try:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
                registered_count += 1
                logger.info(f"✅ Registered blueprint: {blueprint.name} at {url_prefix}")
            except Exception as e:
                logger.error(f"❌ Failed to register {blueprint.name}: {e}")
    
    logger.info(f"📋 Registered {registered_count}/{len(blueprints)} blueprints")
    return registered_count

# ─── Get All Routes Helper ─────────────────────────────────────

def get_all_routes():
    """
    Get a list of all registered route URLs.
    
    Returns:
        List of route URLs
    """
    routes = []
    
    blueprint_routes = [
        ('vin', vin_router),
        ('mpesa', mpesa_bp),
        ('auth', auth_bp),
        ('vehicles', vehicles_bp),
        ('valuations', valuations_bp),
        ('inspections', inspections_bp),
        ('admin', admin_bp),
        ('services', services_bp),
        ('payments', payments_bp),
        ('assessments', assessments_bp),
        ('mileage', mileage_bp),
        ('intelligence', intelligence_bp)
    ]
    
    for name, blueprint in blueprint_routes:
        if blueprint is not None:
            routes.append({
                'name': name,
                'url_prefix': f'/api/{name}',
                'available': True
            })
        else:
            routes.append({
                'name': name,
                'available': False
            })
    
    return routes

# ─── Module Info ──────────────────────────────────────────────

__version__ = '1.0.0'
__author__ = 'AUTO-V Team'
__description__ = 'AUTO-V API Routes Package'

logger.info(f"📦 API Package v{__version__} initialized")
