# services/supabase_client.py - Supabase Client

import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Global client instance
_supabase_client = None

def get_supabase() -> Client:
    """
    Get Supabase client instance (singleton pattern).
    
    Returns:
        Client: Supabase client instance
    
    Raises:
        Exception: If SUPABASE_URL or SUPABASE_KEY is not set
    """
    global _supabase_client
    
    if _supabase_client is None:
        # Get credentials from environment variables
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        # Validate credentials
        if not supabase_url:
            raise Exception("SUPABASE_URL environment variable is not set")
        if not supabase_key:
            raise Exception("SUPABASE_KEY environment variable is not set")
        
        # Log success (without exposing the key)
        logger.info(f"✅ Creating Supabase client for: {supabase_url}")
        
        # Create the client
        _supabase_client = create_client(supabase_url, supabase_key)
    
    return _supabase_client


def get_supabase_client() -> Client:
    """
    Alias for get_supabase() for backward compatibility.
    """
    return get_supabase()


def reset_supabase_client():
    """
    Reset the Supabase client instance.
    Useful for testing or when environment variables change.
    """
    global _supabase_client
    _supabase_client = None
    logger.info("🔄 Supabase client reset")


# ─── Quick Test ──────────────────────────────────────────────
if __name__ == "__main__":
    # Test the connection
    try:
        client = get_supabase()
        logger.info("✅ Supabase client initialized successfully")
        
        # Test a simple query (optional)
        # response = client.table('system_settings').select('*').limit(1).execute()
        # logger.info(f"✅ Test query successful: {response.data}")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
