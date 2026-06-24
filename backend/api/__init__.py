# ============================================================
# API Package Initialization
# ============================================================

from flask import Blueprint

# Create main API blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Import routes to register them
from api.routes import mpesa

# Export blueprints for easy import
__all__ = ["api_bp", "mpesa"]
