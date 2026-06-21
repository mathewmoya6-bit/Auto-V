# services/supabase_client.py - Complete Fix
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ─── SIMPLE CLIENT - NO PROXY ──────────────────────────────────

_supabase_client = None
_supabase_admin_client = None

def get_supabase_client() -> Client:
    """
    Get Supabase client - SIMPLE VERSION without proxy
    
    Returns:
        Client: Supabase client instance
    
    Raises:
        ValueError: If credentials are not set
    """
    global _supabase_client
    
    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url:
            logger.error("❌ SUPABASE_URL is not set")
            raise ValueError("SUPABASE_URL is not set")
        
        if not supabase_key:
            logger.error("❌ SUPABASE_ANON_KEY is not set")
            raise ValueError("SUPABASE_ANON_KEY is not set")
        
        # SIMPLE: Just create client without any extra arguments
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info(f"✅ Supabase client initialized for: {supabase_url}")
    
    return _supabase_client

def get_supabase_admin() -> Optional[Client]:
    """Get admin client with service role"""
    global _supabase_admin_client
    
    if _supabase_admin_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        service_role = os.getenv("SUPABASE_SERVICE_ROLE")
        
        if service_role:
            _supabase_admin_client = create_client(supabase_url, service_role)
            logger.info("✅ Supabase admin client initialized")
        else:
            logger.warning("⚠️ SUPABASE_SERVICE_ROLE not set")
    
    return _supabase_admin_client

def get_supabase():
    """Alias for get_supabase_client()"""
    return get_supabase_client()

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
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Failed to save scan'}
    except Exception as e:
        logger.error(f"Save VIN scan error: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_stats() -> Dict[str, Any]:
    """Get database statistics"""
    try:
        client = get_supabase_client()
        vehicles = client.table('vehicles').select('count', count='exact').execute()
        valuations = client.table('service_requests').select('count', count='exact').eq('service_type', 'valuation').execute()
        inspections = client.table('service_requests').select('count', count='exact').eq('service_type', 'inspection').execute()
        
        return {
            'vehicles': vehicles.count if hasattr(vehicles, 'count') else 0,
            'valuations': valuations.count if hasattr(valuations, 'count') else 0,
            'inspections': inspections.count if hasattr(inspections, 'count') else 0,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get stats error: {str(e)}")
        return {'error': str(e)}

# ─── QUICK TEST ──────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing Supabase Client...")
    try:
        client = get_supabase_client()
        print("✅ Client created successfully")
        health = check_supabase_health()
        print(f"Health: {health}")
    except Exception as e:
        print(f"❌ Error: {e}")
