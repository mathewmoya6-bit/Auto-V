# api/routes/__init__.py - Routes Package

from .auth import auth_bp
from .mpesa import mpesa_bp
from .payments import payments_bp
from .valuations import valuations_bp
from .inspections import inspections_bp
from .assessments import assessments_bp
from .mileage import mileage_bp
from .intelligence import intelligence_bp
from .admin import admin_bp

__all__ = [
    'auth_bp',
    'mpesa_bp',
    'payments_bp',
    'valuations_bp',
    'inspections_bp',
    'assessments_bp',
    'mileage_bp',
    'intelligence_bp',
    'admin_bp'
]
