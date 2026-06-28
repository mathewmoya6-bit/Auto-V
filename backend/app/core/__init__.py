# backend/app/core/__init__.py

from app.core.config import settings
from app.core.database import db, get_db

__all__ = ["settings", "db", "get_db"]
