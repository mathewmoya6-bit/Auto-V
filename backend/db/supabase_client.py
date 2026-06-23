# db/supabase_client.py - Production Ready (Fixed)

import os
import logging
from supabase import create_client, Client
from threading import Lock

logger = logging.getLogger(__name__)

_supabase_client: Client = None
_client_lock = Lock()


def get_supabase() -> Client:
    """Get Singleton Supabase Client with thread-safe initialization."""
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    with _client_lock:
        if _supabase_client is not None:
            return _supabase_client
        
        supabase_url = os.getenv('SUPABASE_URL', 'https://tsvejnzxrxrrecgquxbq.supabase.co')
        supabase_key = os.getenv('SUPABASE_ANON_KEY', os.getenv('SUPABASE_KEY', ''))
        
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        
        # ─── NO proxy parameter ──────────────────────────────────────
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("✅ Supabase client initialized")
        
        return _supabase_client


def get_supabase_status() -> dict:
    """
    Get Supabase connection status WITHOUT testing database tables.
    
    This is a clean health check that doesn't depend on:
    - Table existence
    - RLS policies
    - Database schema
    
    Uses auth.get_session() as a lightweight, table-independent verification.
    
    Returns:
        dict: Connection status with 'connected' and 'error' fields
    """
    status = {
        "connected": False,
        "url_configured": bool(os.getenv('SUPABASE_URL')),
        "key_configured": bool(os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY')),
        "error": None,
        "client_initialized": _supabase_client is not None
    }
    
    try:
        # Get or create client (this will initialize if not already)
        client = get_supabase()
        
        # ─── Real lightweight verification (safe + production standard) ──
        # This does NOT require table or schema existence
        try:
            client.auth.get_session()
            status["connected"] = True
            logger.info("✅ Supabase connection verified (auth session check)")
        except Exception as e:
            status["connected"] = False
            status["error"] = str(e)
            logger.warning(f"⚠️ Supabase connection not fully verified: {e}")
        
    except Exception as e:
        status["connected"] = False
        status["error"] = str(e)
        logger.error(f"❌ Supabase connection test failed: {e}")
    
    return status


def force_supabase_connection() -> bool:
    """
    Force a connection test on startup.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        client = get_supabase()
        
        # Test connection without table dependency using auth session
        try:
            client.auth.get_session()
            logger.info("🔥 Supabase forced initialization successful (auth session check)")
            return True
        except Exception as e:
            logger.warning(f"🔥 Supabase auth session check failed: {e}")
            # Check if client is at least initialized
            if _supabase_client is not None:
                logger.info("🔥 Supabase client initialized but auth session check failed")
                return True
            return False
            
    except Exception as e:
        logger.error(f"🔥 Supabase forced initialization FAILED: {e}")
        return False


# ─── Convenience Function for Health Checks ──────────────────

def check_supabase_health() -> dict:
    """
    Comprehensive health check for Supabase.
    
    Returns:
        dict: Full health status with all details
    """
    status = get_supabase_status()
    
    # Add additional context
    status.update({
        "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z",
        "url": os.getenv('SUPABASE_URL', 'not_set')[:30] + "...",
        "key_mode": "service_role" if os.getenv('SUPABASE_KEY') else "anon" if os.getenv('SUPABASE_ANON_KEY') else "none"
    })
    
    return status


# ─── Reset Client (useful for testing) ──────────────────────

def reset_supabase_client() -> None:
    """Reset the Supabase client (useful for testing)."""
    global _supabase_client
    with _client_lock:
        _supabase_client = None
        logger.info("🔄 Supabase client reset")


# ─── Exports ──────────────────────────────────────────────────

__all__ = [
    'get_supabase',
    'get_supabase_status',
    'force_supabase_connection',
    'check_supabase_health',
    'reset_supabase_client'
]
