# backend/services/supabase_client.py
from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_supabase():
    """Get Supabase client instance"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    
    return create_client(url, key)

# Create a singleton instance
_supabase_client = None

def get_supabase_client():
    """Get or create Supabase client singleton"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = get_supabase()
    return _supabase_client
