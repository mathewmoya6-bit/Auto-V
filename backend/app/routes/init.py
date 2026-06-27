# backend/app/routes/__init__.py
# This makes 'app.routes' a Python package

from app.routes import health, auth

__all__ = ['health', 'auth']
