# api/__init__.py - API Package

import logging

logger = logging.getLogger(__name__)

# ─── Import from routes package ──────────────────────────────
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
    from .routes.admin import admin_bp
    logger.info("✅ Admin routes loaded")
except ImportError as e:
    logger.warning(f"⚠️ Admin routes not available: {e}")
    admin_bp = None

# ─── Register Blueprints Helper ────────────────────────────────

def register_blueprints(app):
    """Register all blueprints to the Flask app."""
    blueprints = [
        (mpesa_bp, '/api/mpesa', 'M-Pesa'),
        (auth_bp, '/api/auth', 'Auth'),
        (admin_bp, '/api/admin', 'Admin'),
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

# ─── Export ──────────────────────────────────────────────────────

__all__ = ['mpesa_bp', 'auth_bp', 'admin_bp', 'register_blueprints']
