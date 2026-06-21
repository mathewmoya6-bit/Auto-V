# services/supabase_client.py - FINAL PRODUCTION READY (No proxy)

import os
import logging
from threading import Lock
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_supabase_client: Client = None
_supabase_admin_client: Client = None
_client_lock = Lock()


# ─── PUBLIC CLIENT (ANON ROLE) ──────────────────────────────────────

def get_supabase_client() -> Client:
    """
    Get Supabase client instance (anon role).
    FORCE NO PROXY - cleans environment variables.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    with _client_lock:
        if _supabase_client is not None:
            return _supabase_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url:
            raise ValueError("SUPABASE_URL environment variable is not set")
        if not supabase_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is not set")

        # ─── CRITICAL: Clear proxy environment variables ──────────
        for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]
                logger.info(f"✅ Removed {proxy_var}")

        # ─── Initialize client ──────────────────────────────────────
        try:
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase client initialized (no proxy)")
        except TypeError as e:
            if 'proxy' in str(e):
                logger.warning(f"⚠️ Proxy error, using custom HTTP client")
                import httpx
                http_client = httpx.Client(proxies=None, timeout=30.0, follow_redirects=True)
                _supabase_client = create_client(supabase_url, supabase_key, http_client=http_client)
                logger.info("✅ Supabase client initialized with custom HTTP client (no proxy)")
            else:
                raise

        return _supabase_client


# ─── ADMIN CLIENT (SERVICE ROLE) ────────────────────────────────────

def get_supabase_admin() -> Client:
    """
    Get Supabase admin client (service role).
    FORCE NO PROXY - cleans environment variables.
    """
    global _supabase_admin_client

    if _supabase_admin_client is not None:
        return _supabase_admin_client

    with _client_lock:
        if _supabase_admin_client is not None:
            return _supabase_admin_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_service_role = os.getenv("SUPABASE_SERVICE_ROLE")

        if not supabase_url:
            raise ValueError("SUPABASE_URL environment variable is not set")
        if not supabase_service_role:
            raise ValueError("SUPABASE_SERVICE_ROLE environment variable is not set")

        # ─── CRITICAL: Clear proxy environment variables ──────────
        for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]
                logger.info(f"✅ Removed {proxy_var}")

        # ─── Initialize admin client ──────────────────────────────
        try:
            _supabase_admin_client = create_client(supabase_url, supabase_service_role)
            logger.info("✅ Supabase admin client initialized (no proxy)")
        except TypeError as e:
            if 'proxy' in str(e):
                logger.warning(f"⚠️ Proxy error on admin client, using custom HTTP client")
                import httpx
                http_client = httpx.Client(proxies=None, timeout=30.0, follow_redirects=True)
                _supabase_admin_client = create_client(supabase_url, supabase_service_role, http_client=http_client)
                logger.info("✅ Supabase admin client initialized with custom HTTP client (no proxy)")
            else:
                raise

        return _supabase_admin_client


# ─── ALIAS ──────────────────────────────────────────────────────────

def get_supabase():
    """
    Alias for get_supabase_client().
    """
    return get_supabase_client()


# ─── RESET (for testing) ────────────────────────────────────────────

def reset_supabase_clients():
    """
    Reset Supabase clients (useful for testing).
    """
    global _supabase_client, _supabase_admin_client
    _supabase_client = None
    _supabase_admin_client = None
    logger.info("🔄 Supabase clients reset")


# ─── TEST CONNECTION ────────────────────────────────────────────────

def test_connection() -> bool:
    """
    Test Supabase connection.
    """
    try:
        client = get_supabase_client()
        response = client.table('system_settings').select('*').limit(1).execute()
        logger.info("✅ Supabase connection test successful")
        return True
    except Exception as e:
        logger.error(f"❌ Supabase connection test failed: {e}")
        return False


# ─── QUICK TEST ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing Supabase Client...")
    try:
        client = get_supabase_client()
        print("✅ Public client created successfully")
        
        # Try to test connection
        if test_connection():
            print("✅ Connection test passed")
        else:
            print("❌ Connection test failed")
            
        print("✅ Supabase client test complete")
    except Exception as e:
        print(f"❌ Error: {e}")
