# app/core/database.py
# =============================================================================
# AUTO-V API - Database Core (Supabase Native)
# =============================================================================

import logging
from typing import Optional, Generator
from contextlib import contextmanager
from functools import lru_cache

from supabase import create_client, Client
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Client Container ─────────────────────────────────────────────────

class SupabaseClients:
    """Container for Supabase clients."""
    
    def __init__(self):
        self._public: Optional[Client] = None
        self._admin: Optional[Client] = None
        self._initialized: bool = False
    
    @property
    def public(self) -> Client:
        if not self._public:
            raise RuntimeError("Supabase public client not initialized")
        return self._public
    
    @property
    def admin(self) -> Client:
        if not self._admin:
            raise RuntimeError("Supabase admin client not initialized")
        return self._admin
    
    @property
    def initialized(self) -> bool:
        return self._initialized
    
    def init(self) -> bool:
        try:
            if not settings.supabase_configured:
                logger.warning("⚠️  Supabase credentials not configured")
                return False
            
            self._public = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_ANON_KEY
            )
            logger.info("✅ Supabase public client initialized")
            
            if settings.SUPABASE_SERVICE_ROLE_KEY:
                self._admin = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_ROLE_KEY
                )
                logger.info("✅ Supabase admin client initialized")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase: {e}")
            self._initialized = False
            return False
    
    def reset(self) -> None:
        self._public = None
        self._admin = None
        self._initialized = False


# ─── Singleton ──────────────────────────────────────────────────────

_clients = SupabaseClients()


def init_supabase() -> bool:
    """Initialize Supabase clients. Call during FastAPI startup."""
    return _clients.init()


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Get the public Supabase client."""
    return _clients.public


@lru_cache(maxsize=1)
def get_admin_client() -> Client:
    """Get the admin Supabase client (with service role key)."""
    return _clients.admin


def is_configured() -> bool:
    """Check if Supabase is configured and initialized."""
    return _clients.initialized


# ─── Dependency Injection ──────────────────────────────────────────

def get_db() -> Generator[Client, None, None]:
    """Dependency injection for Supabase client."""
    if not _clients.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured"
        )
    yield _clients.public


def get_db_admin() -> Generator[Client, None, None]:
    """Dependency injection for admin Supabase client."""
    if not _clients.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured"
        )
    if not _clients.admin:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin database client not configured"
        )
    yield _clients.admin


__all__ = [
    "init_supabase",
    "get_supabase",
    "get_admin_client",
    "is_configured",
    "get_db",
    "get_db_admin",
]
