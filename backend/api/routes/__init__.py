# api/__init__.py - AUTO-V API Routes Package
import logging
from flask import Blueprint

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

# ─── Fixed: Use correct filenames ──────────────────────────────
# inspections_bp → inspection_bp (singular)
try:
    from .routes.inspection import inspection_bp
    logger.info("✅ Inspection routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Inspection routes not available: {e}")
    inspection_bp = None

# intelligence_bp → intelligence_bp (if file exists)
try:
    from .routes.intelligence import intelligence_bp
    logger.info("✅ Intelligence routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Intelligence routes not available: {e}")
    intelligence_bp = None

# ─── M-Pesa routes ──────────────────────────────────────────────
try:
    from .routes.mpesa import mpesa_bp
    logger.info("✅ M-Pesa routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ M-Pesa routes not available: {e}")
    mpesa_bp = None

# payments_bp → payments_bp (if file exists)
try:
    from .routes.payments import payments_bp
    logger.info("✅ Payment routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Payment routes not available: {e}")
    payments_bp = None

# ─── Fixed: valuations_bp → valuation_bp (singular) ────────────
try:
    from .routes.valuation import valuation_bp
    logger.info("✅ Valuation routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Valuation routes not available: {e}")
    valuation_bp = None

# ─── Fixed: vehicles_bp ─────────────────────────────────────────
try:
    from .routes.vehicles import vehicles_bp
    logger.info("✅ Vehicle routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Vehicle routes not available: {e}")
    vehicles_bp = None

# ─── Fixed: services_bp ─────────────────────────────────────────
try:
    from .routes.services import services_bp
    logger.info("✅ Service routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Service routes not available: {e}")
    services_bp = None

# ─── Fixed: assessments_bp → assessment_bp (singular) ──────────
try:
    from .routes.assessment import assessment_bp
    logger.info("✅ Assessment routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Assessment routes not available: {e}")
    assessment_bp = None

# ─── Fixed: mileage_bp ──────────────────────────────────────────
try:
    from .routes.mileage import mileage_bp
    logger.info("✅ Mileage routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Mileage routes not available: {e}")
    mileage_bp = None

# ─── Fixed: vin_routes ──────────────────────────────────────────
try:
    from .routes.vin import vin_bp
    logger.info("✅ VIN routes loaded")
except ImportError as e:
    try:
        # Fallback for different naming
        from .routes.vin_routes import vin_bp
        logger.info("✅ VIN routes loaded (from vin_routes)")
    except ImportError as e2:
        logger.warning(f"⚠️ VIN routes not available: {e2}")
        vin_bp = None

# ─── Fleet routes ──────────────────────────────────────────────
try:
    from .routes.fleet import fleet_bp
    logger.info("✅ Fleet routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Fleet routes not available: {e}")
    fleet_bp = None

# ─── Verify routes ──────────────────────────────────────────────
try:
    from .routes.verify import verify_bp
    logger.info("✅ Verify routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Verify routes not available: {e}")
    verify_bp = None

# ─── Export All Blueprints ──────────────────────────────────────

__all__ = [
    'admin_bp',
    'auth_bp',
    'inspection_bp',
    'intelligence_bp',
    'mpesa_bp',
    'payments_bp',
    'valuation_bp',
    'vehicles_bp',
    'services_bp',
    'assessment_bp',
    'mileage_bp',
    'vin_bp',
    'fleet_bp',
    'verify_bp'
]

# ─── Register Blueprints Helper ────────────────────────────────

def register_blueprints(app):
    """Register all blueprints to the Flask app."""
    blueprints = [
        (admin_bp, '/api/admin', 'Admin'),
        (auth_bp, '/api/auth', 'Auth'),
        (inspection_bp, '/api/inspection', 'Inspection'),
        (intelligence_bp, '/api/intelligence', 'Intelligence'),
        (mpesa_bp, '/api/mpesa', 'M-Pesa'),
        (payments_bp, '/api/payments', 'Payments'),
        (valuation_bp, '/api/valuation', 'Valuation'),
        (vehicles_bp, '/api/vehicles', 'Vehicles'),
        (services_bp, '/api/services', 'Services'),
        (assessment_bp, '/api/assessment', 'Assessment'),
        (mileage_bp, '/api/mileage', 'Mileage'),
        (vin_bp, '/api/vin', 'VIN'),
        (fleet_bp, '/api/fleet', 'Fleet'),
        (verify_bp, '/api/verify', 'Verify')
    ]
    
    registered_count = 0
    for blueprint, url_prefix, name in blueprints:
        if blueprint is not None:
            try:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
                registered_count += 1
                logger.info(f"✅ Registered: {name} at {url_prefix}")
            except Exception as e:
                logger.error(f"❌ Failed to register {name}: {e}")
        else:
            logger.debug(f"⏭️ Skipping {name} (not available)")
    
    logger.info(f"📋 Registered {registered_count}/{len(blueprints)} blueprints")
    return registered_count

# ─── Get Available Routes Helper ──────────────────────────────

def get_available_routes():
    """Return list of available route names."""
    available = []
    for name in __all__:
        if globals().get(name) is not None:
            available.append(name.replace('_bp', ''))
    return available

def is_route_available(route_name):
    """Check if a specific route is available."""
    bp_name = f"{route_name}_bp"
    return globals().get(bp_name) is not None
