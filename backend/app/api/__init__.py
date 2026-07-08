# app/api/__init__.py
# =============================================================================
# AUTO-V API - API Package
# =============================================================================
"""
Intentionally empty. Do NOT import api_router here — main.py imports it
directly from app.api.v1.api. Re-importing it at this level too (as the
old repo did) is what caused the original circular-import chain.
"""
