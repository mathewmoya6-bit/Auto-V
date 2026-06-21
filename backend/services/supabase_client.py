# services/supabase_client.py - FINAL FIX (No proxy)

import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_supabase_client = None

def get_supabase_client() -> Client:
    """Get Supabase client instance - FORCE NO PROXY."""
    global _supabase_client
    
    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url:
            raise ValueError("SUPABASE_URL environment variable is not set")
        if not supabase_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is not set")
        
        # ─── CRITICAL: Clear proxy environment variables ──────────
        # The supabase client reads these automatically
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        os.environ.pop('http_proxy', None)
        os.environ.pop('https_proxy', None)
        
        # ─── Initialize client ──────────────────────────────────────
        try:
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase client initialized")
        except TypeError as e:
            if 'proxy' in str(e):
                logger.error(f"❌ Proxy error: {e}")
                # Try with explicit no proxy
                import httpx
                http_client = httpx.Client(proxies=None)
                _supabase_client = create_client(supabase_url, supabase_key, http_client=http_client)
                logger.info("✅ Supabase client initialized with no proxy")
            else:
                raise
    
    return _supabase_client

def get_supabase():
    """Alias for get_supabase_client()."""
    return get_supabase_client()
