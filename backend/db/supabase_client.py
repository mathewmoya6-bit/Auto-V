# db/supabase_client.py - FIXED

import os
import logging
from supabase import create_client, Client
from threading import Lock

logger = logging.getLogger(__name__)

_supabase_client: Client = None
_client_lock = Lock()

def get_supabase() -> Client:
    """Get Singleton Supabase Client."""
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
