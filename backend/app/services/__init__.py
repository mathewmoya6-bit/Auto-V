# app/__init__.py
"""AUTO-V Professional Valuation Engine - Backend Application"""

__version__ = "2.0.0"
__app_name__ = "AUTO-V API"

from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging on import
setup_logging()
