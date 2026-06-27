# backend/app/core/__init__.py
# This makes 'app.core' a Python package

from app.core.config import settings
from app.core.database import supabase

__all__ = ['settings', 'supabase']
