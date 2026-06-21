# api/routes/__init__.py - Routes Package
"""
AUTO-V API Routes Package
Contains all route blueprints organized by service
"""

import logging

logger = logging.getLogger(__name__)

# ─── M-Pesa Routes ──────────────────────────────────────────────
try:
    from .mpesa import mpesa_bp
    logger.info("✅ M-Pesa blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ M-Pesa blueprint not available: {e}")
    mpesa_bp = None

# ─── Auth Routes ────────────────────────────────────────────────
try:
    from .auth import auth_bp
    logger.info("✅ Auth blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Auth blueprint not available: {e}")
    auth_bp = None

# ─── Admin Routes ───────────────────────────────────────────────
try:
    from .admin import admin_bp
    logger.info("✅ Admin blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Admin blueprint not available: {e}")
    admin_bp = None

# ─── Vehicle Routes ─────────────────────────────────────────────
try:
    from .vehicles import vehicles_bp
    logger.info("✅ Vehicles blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Vehicles blueprint not available: {e}")
    vehicles_bp = None

# ─── Valuation Routes ───────────────────────────────────────────
try:
    from .valuations import valuations_bp
    logger.info("✅ Valuations blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Valuations blueprint not available: {e}")
    valuations_bp = None

# ─── Inspection Routes ──────────────────────────────────────────
try:
    from .inspections import inspections_bp
    logger.info("✅ Inspections blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Inspections blueprint not available: {e}")
    inspections_bp = None

# ─── Assessment Routes ──────────────────────────────────────────
try:
    from .assessments import assessments_bp
    logger.info("✅ Assessments blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Assessments blueprint not available: {e}")
    assessments_bp = None

# ─── Mileage Routes ─────────────────────────────────────────────
try:
    from .mileage import mileage_bp
    logger.info("✅ Mileage blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Mileage blueprint not available: {e}")
    mileage_bp = None

# ─── Service Routes ─────────────────────────────────────────────
try:
    from .services import services_bp
    logger.info("✅ Services blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Services blueprint not available: {e}")
    services_bp = None

# ─── Payment Routes ─────────────────────────────────────────────
try:
    from .payments import payments_bp
    logger.info("✅ Payments blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Payments blueprint not available: {e}")
    payments_bp = None

# ─── Intelligence Routes ────────────────────────────────────────
try:
    from .intelligence import intelligence_bp
    logger.info("✅ Intelligence blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Intelligence blueprint not available: {e}")
    intelligence_bp = None

# ─── VIN Routes ──────────────────────────────────────────────────
try:
    from .vin_routes import router as vin_router
    logger.info("✅ VIN routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ VIN routes not available: {e}")
    vin_router = None

# ─── Export All Blueprints ──────────────────────────────────────

__all__ = [
    'mpesa_bp',
    'auth_bp',
    'admin_bp',
    'vehicles_bp',
    'valuations_bp',
    'inspections_bp',
    'assessments_bp',
    'mileage_bp',
    'services_bp',
    'payments_bp',
    'intelligence_bp',
    'vin_router'
]

# ─── Blueprint Registration Helper ──────────────────────────────

def register_all_blueprints(app):
    """
    Register all available blueprints to the Flask app.
    
    Args:
        app: Flask application instance
        
    Returns:
        int: Number of successfully registered blueprints
    """
    blueprints = [
        (mpesa_bp, '/api/mpesa'),
        (auth_bp, '/api/auth'),
        (admin_bp, '/api/admin'),
        (vehicles_bp, '/api/vehicles'),
        (valuations_bp, '/api/valuations'),
        (inspections_bp, '/api/inspections'),
        (assessments_bp, '/api/assessments'),
        (mileage_bp, '/api/mileage'),
        (services_bp, '/api/services'),
        (payments_bp, '/api/payments'),
        (intelligence_bp, '/api/intelligence'),
        (vin_router, '/api/vin')
    ]
    
    registered_count = 0
    for blueprint, url_prefix in blueprints:
        if blueprint is not None:
            try:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
                registered_count += 1
                logger.info(f"✅ Registered: {url_prefix}")
            except Exception as e:
                logger.error(f"❌ Failed to register {url_prefix}: {e}")
    
    logger.info(f"📋 Registered {registered_count}/{len(blueprints)} blueprints")
    return registered_count

# ─── Get All Routes Helper ──────────────────────────────────────

def get_all_routes():
    """
    Get a list of all registered route URLs.
    
    Returns:
        list: Route information
    """
    routes = []
    
    blueprint_info = [
        ('mpesa', mpesa_bp, '/api/mpesa'),
        ('auth', auth_bp, '/api/auth'),
        ('admin', admin_bp, '/api/admin'),
        ('vehicles', vehicles_bp, '/api/vehicles'),
        ('valuations', valuations_bp, '/api/valuations'),
        ('inspections', inspections_bp, '/api/inspections'),
        ('assessments', assessments_bp, '/api/assessments'),
        ('mileage', mileage_bp, '/api/mileage'),
        ('services', services_bp, '/api/services'),
        ('payments', payments_bp, '/api/payments'),
        ('intelligence', intelligence_bp, '/api/intelligence'),
        ('vin', vin_router, '/api/vin')
    ]
    
    for name, blueprint, prefix in blueprint_info:
        if blueprint is not None:
            routes.append({
                'name': name,
                'url_prefix': prefix,
                'available': True
            })
        else:
            routes.append({
                'name': name,
                'available': False
            })
    
    return routes

# ─── Package Info ────────────────────────────────────────────────

__version__ = '1.0.0'
__author__ = 'AUTO-V Team'
__description__ = 'AUTO-V API Routes Package'

logger.info(f"📦 Routes Package v{__version__} initialized")
