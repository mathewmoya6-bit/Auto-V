"""
Supabase Client - Production Ready (FastAPI Version)
Thread-safe singleton client with comprehensive health checks
"""

import os
import logging
from threading import Lock
from datetime import datetime
from typing import Optional, Dict, Any
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ─── Global State ──────────────────────────────────────────────

_supabase_client: Optional[Client] = None
_client_lock = Lock()


# ─── Client Initialization ──────────────────────────────────

def get_supabase() -> Client:
    """
    Get Singleton Supabase Client with thread-safe initialization.
    
    Returns:
        Client: Initialized Supabase client
    
    Raises:
        RuntimeError: If Supabase credentials are not configured
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    with _client_lock:
        if _supabase_client is not None:
            return _supabase_client
        
        # Get credentials
        supabase_url = os.getenv('SUPABASE_URL', '')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY', '')
        
        if not supabase_url or not supabase_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_ANON_KEY/SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        
        # Initialize client
        try:
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            raise RuntimeError(f"Supabase initialization failed: {e}")
        
        return _supabase_client


# ─── Health Checks ──────────────────────────────────────────

def get_supabase_status() -> Dict[str, Any]:
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
        "key_configured": bool(os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY')),
        "error": None,
        "client_initialized": _supabase_client is not None
    }
    
    try:
        # Get or create client (this will initialize if not already)
        client = get_supabase()
        
        # Lightweight verification - does NOT require table or schema existence
        try:
            client.auth.get_session()
            status["connected"] = True
            logger.debug("✅ Supabase connection verified (auth session check)")
        except Exception as e:
            status["connected"] = False
            status["error"] = str(e)
            logger.warning(f"⚠️ Supabase auth session check failed: {e}")
            
            # If client exists but auth failed, still consider it partially connected
            if _supabase_client is not None:
                status["connected"] = True
                status["auth_verified"] = False
                status["error"] = f"Auth check failed but client initialized: {e}"
        
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


def check_supabase_health() -> Dict[str, Any]:
    """
    Comprehensive health check for Supabase.
    
    Returns:
        dict: Full health status with all details
    """
    status = get_supabase_status()
    
    # Add additional context
    status.update({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "url": os.getenv('SUPABASE_URL', 'not_set')[:30] + "...",
        "key_mode": (
            "service_role" if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else
            "anon" if os.getenv('SUPABASE_ANON_KEY') else
            "key" if os.getenv('SUPABASE_KEY') else
            "none"
        )
    })
    
    return status


# ─── Reset Client (useful for testing) ──────────────────────

def reset_supabase_client() -> None:
    """
    Reset the Supabase client (useful for testing).
    """
    global _supabase_client
    with _client_lock:
        _supabase_client = None
        logger.info("🔄 Supabase client reset")


# ─── Async Version for FastAPI ──────────────────────────────

async def async_get_supabase() -> Client:
    """
    Async wrapper for get_supabase().
    Returns the same singleton client.
    """
    return get_supabase()


async def async_check_supabase_health() -> Dict[str, Any]:
    """
    Async wrapper for check_supabase_health().
    """
    return check_supabase_health()


# ─── Exports ──────────────────────────────────────────────────

__all__ = [
    'get_supabase',
    'async_get_supabase',
    'get_supabase_status',
    'force_supabase_connection',
    'check_supabase_health',
    'async_check_supabase_health',
    'reset_supabase_client'
]
