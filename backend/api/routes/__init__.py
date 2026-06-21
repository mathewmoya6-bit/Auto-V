# api/routes/__init__.py - Routes Package

import logging

logger = logging.getLogger(__name__)

# ─── Import M-Pesa routes ──────────────────────────────────
try:
    from .mpesa import mpesa_bp
    logger.info("✅ M-Pesa blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ M-Pesa blueprint not available: {e}")
    mpesa_bp = None

# ─── Import Auth routes ────────────────────────────────────
try:
    from .auth import auth_bp
    logger.info("✅ Auth blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Auth blueprint not available: {e}")
    auth_bp = None

# ─── Import Admin routes ───────────────────────────────────
try:
    from .admin import admin_bp
    logger.info("✅ Admin blueprint loaded")
except ImportError as e:
    logger.warning(f"⚠️ Admin blueprint not available: {e}")
    admin_bp = None

# ─── Export ──────────────────────────────────────────────────

__all__ = ['mpesa_bp', 'auth_bp', 'admin_bp']
