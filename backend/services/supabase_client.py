# services/supabase_client.py - Supabase Client

import os
from supabase import create_client, Client

_supabase_client = None

def get_supabase() -> Client:
    """Get Supabase client instance (singleton)."""
    global _supabase_client
    
    if _supabase_client is None:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise Exception("SUPABASE_URL and SUPABASE_KEY must be set")
        
        _supabase_client = create_client(supabase_url, supabase_key)
    
    return _supabase_client
