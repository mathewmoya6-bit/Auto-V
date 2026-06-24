# ============================================================
# services/supabase_client.py - Supabase Client Wrapper
# ============================================================

import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

_supabase_client = None

def get_supabase_client():
    """Get Supabase client instance (singleton)."""
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    try:
        from supabase import create_client
        
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("✅ Supabase client initialized")
        return _supabase_client
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
        raise
