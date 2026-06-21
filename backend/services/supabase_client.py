# services/supabase_client.py - Fixed Supabase Client
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ─── SUPABASE CLIENT ──────────────────────────────────────────

class SupabaseClient:
    """Fixed Supabase client without proxy argument"""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.service_role = os.getenv("SUPABASE_SERVICE_ROLE")
        
        if not self.url:
            raise ValueError("SUPABASE_URL environment variable is not set")
        if not self.anon_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is not set")
        
        # Initialize client without proxy
        self.client: Client = create_client(self.url, self.anon_key)
        self.admin_client: Optional[Client] = None
        
        if self.service_role:
            self.admin_client = create_client(self.url, self.service_role)
            logger.info("✅ Admin client initialized")
        
        logger.info(f"✅ Supabase client initialized for: {self.url}")

    def get_client(self) -> Client:
        """Get the Supabase client"""
        return self.client

    def get_table(self, table_name: str):
        """Get a table reference"""
        return self.client.table(table_name)

    def get_storage(self, bucket_name: str):
        """Get a storage bucket reference"""
        return self.client.storage.from_(bucket_name)

# ─── SINGLETON INSTANCE ──────────────────────────────────────

_supabase_client = None

def get_supabase() -> SupabaseClient:
    """Get Supabase client instance (singleton)"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client

def get_supabase_client() -> Client:
    """Get the raw Supabase client"""
    return get_supabase().get_client()

def check_supabase_health() -> Dict[str, Any]:
    """Check Supabase connection health"""
    try:
        client = get_supabase_client()
        # Simple query to test connection
        response = client.table('system_settings').select('*').limit(1).execute()
        return {
            'connected': True,
            'message': 'Supabase connection successful',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Supabase health check failed: {str(e)}")
        return {
            'connected': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# ─── CONVENIENCE FUNCTIONS ──────────────────────────────────

def get_vehicle_by_vin(vin: str) -> List[Dict[str, Any]]:
    """Get vehicle by VIN"""
    try:
        client = get_supabase_client()
        response = client.table('vehicles').select('*').eq('vin', vin).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get vehicle by VIN error: {str(e)}")
        return []

def save_vin_scan(user_id: str, vin: str, image_url: str, status: str = 'pending') -> Dict[str, Any]:
    """Save VIN scan record"""
    try:
        client = get_supabase_client()
        data = {
            'user_id': user_id,
            'vin': vin,
            'image_url': image_url,
            'status': status,
            'created_at': datetime.now().isoformat()
        }
        response = client.table('vin_scans').insert(data).execute()
        return {'success': True, 'data': response.data[0]} if response.data else {'success': False, 'error': 'Failed to save scan'}
    except Exception as e:
        logger.error(f"Save VIN scan error: {str(e)}")
        return {'success': False, 'error': str(e)}

# ─── QUICK TEST ──────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing Supabase Client...")
    try:
        health = check_supabase_health()
        print(f"Health: {health}")
    except Exception as e:
        print(f"❌ Error: {e}")
