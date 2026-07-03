# app/models/__init__.py
# =============================================================================
# AUTO-V API - Models Package
# =============================================================================

from app.core.database import Base
from app.models.user import UserProfile

__all__ = [
    "Base",
    "UserProfile",
]
