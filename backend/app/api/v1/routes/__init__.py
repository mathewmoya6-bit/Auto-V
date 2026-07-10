# app/api/v1/routes/__init__.py
# =============================================================================
# AUTO-V API - Routes Package (Version 1)
# =============================================================================
"""
Add one line here per domain, only once that domain's route file exists
and its own imports are verified. Do not import services or schemas here —
this file only ever imports route modules.
"""
from . import auth
from . import vehicles
from . import valuations
from . import mileage
from . import inspections

__all__ = ["auth", "vehicles", "valuations", "mileage", "inspections"]
