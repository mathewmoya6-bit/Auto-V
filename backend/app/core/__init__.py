# app/core/__init__.py
# =============================================================================
# AUTO-V API - Core Package
# =============================================================================
"""
Intentionally empty of imports. Import directly from submodules:
    from app.core.config import settings
    from app.core.database import get_supabase, get_admin_client
    from app.core.security import get_current_user, hash_password, ...

Never add `from app.core.X import Y` here — an __init__.py that eagerly
imports every submodule is what caused the circular-import chain earlier
(auth -> services/__init__ -> payment_service -> broken import -> every
route dies, not just payments). Keep this file empty.
"""
