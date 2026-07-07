# app/core/database.py
# =============================================================================
# AUTO-V API - Database Core (Supabase Native)
# =============================================================================

import os
import logging
from typing import Optional, Dict, Any, Generator
from supabase import create_client, Client

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Supabase Clients ─────────────────────────────────────────────────

# Public client (uses anon key)
supabase: Optional[Client] = None

# Admin client (uses service role key)
supabase_admin: Optional[Client] = None


def init_supabase() -> bool:
    """
    Initialize Supabase clients from settings.
    
    Returns:
        True if initialized successfully, False otherwise
    """
    global supabase, supabase_admin
    
    if not settings.supabase_configured:
        logger.warning("⚠️  Supabase credentials not configured")
        return False
    
    try:
        # Public client
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        logger.info("✅ Supabase public client initialized")
        
        # Admin client (if service role key is available)
        if settings.SUPABASE_SERVICE_ROLE_KEY:
            supabase_admin = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            logger.info("✅ Supabase admin client initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase: {e}")
        return False


# ─── Client Getter Functions ─────────────────────────────────────────

def get_supabase() -> Optional[Client]:
    """
    Get the public Supabase client.
    
    Use this for regular authenticated requests.
    
    Returns:
        Supabase client instance or None if not initialized
    """
    return supabase


def get_admin_client() -> Optional[Client]:
    """
    Get the admin Supabase client (with service role key).
    
    Use this for admin operations that bypass RLS.
    
    Returns:
        Supabase admin client instance or None if not initialized
    """
    return supabase_admin


def is_configured() -> bool:
    """
    Check if Supabase is configured.
    
    Returns:
        True if Supabase is configured, False otherwise
    """
    return supabase is not None


# ─── Compatibility Layer (For Routes Being Migrated) ─────────────────

def get_db() -> Generator[Client, None, None]:
    """
    Compatibility wrapper for old SQLAlchemy routes.
    
    This allows routes still using `Depends(get_db)` to work during migration.
    
    ⚠️ DEPRECATED: New routes should use `get_supabase()` directly.
    
    Yields:
        Supabase client instance
    """
    if not supabase:
        raise Exception("Supabase not configured")
    
    yield supabase


def get_db_admin() -> Generator[Client, None, None]:
    """
    Compatibility wrapper for admin routes.
    
    ⚠️ DEPRECATED: New routes should use `get_admin_client()` directly.
    
    Yields:
        Supabase admin client instance
    """
    if not supabase_admin:
        raise Exception("Supabase admin client not configured")
    
    yield supabase_admin


# ─── SQLAlchemy Compatibility (For Routes Still Using SQLAlchemy) ────

# ⚠️ These are stub functions for routes still using SQLAlchemy
# They will raise errors if called - helping identify routes that need migration

class SQLAlchemyStub:
    """
    Stub class to catch SQLAlchemy calls during migration.
    """
    def __getattr__(self, name):
        raise AttributeError(
            f"SQLAlchemy is no longer supported. "
            f"Use supabase.table('{name}').select('*').execute() instead. "
            f"Attempted to call: {name}"
        )


# ─── Helper Functions ────────────────────────────────────────────────

async def execute_query(table: str, query: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute a Supabase query.
    
    Args:
        table: Table name
        query: Query parameters (select, filter, etc.)
        
    Returns:
        Query result
    """
    if not supabase:
        raise Exception("Supabase not configured")
    
    try:
        # Build query
        q = supabase.table(table)
        
        if query:
            # Handle select
            if "select" in query:
                q = q.select(query["select"])
            else:
                q = q.select("*")
            
            # Handle filters
            if "filter" in query:
                for key, value in query["filter"].items():
                    q = q.eq(key, value)
            
            # Handle order
            if "order" in query:
                q = q.order(query["order"]["column"], desc=query["order"].get("desc", False))
            
            # Handle limit
            if "limit" in query:
                q = q.limit(query["limit"])
            
            # Handle range
            if "range" in query:
                q = q.range(query["range"]["start"], query["range"]["end"])
        
        result = q.execute()
        return {
            "success": True,
            "data": result.data,
            "count": len(result.data) if result.data else 0
        }
        
    except Exception as e:
        logger.error(f"❌ Query error: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


# ─── Initialize on Import ────────────────────────────────────────────

# Auto-initialize
init_supabase()


# ─── Module Logger ──────────────────────────────────────────────────

logger = logging.getLogger(__name__)
logger.info("📦 Database module loaded")
logger.info(f"🔗 Supabase configured: {is_configured()}")
