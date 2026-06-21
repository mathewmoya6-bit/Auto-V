# services/supabase_client.py - COMPLETE PRODUCTION READY

import os
import logging
from threading import Lock
from datetime import datetime
from typing import Dict, Any, Optional
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


# ─── RESET CLIENTS ──────────────────────────────────────────────────

def reset_supabase_client():
    """
    Reset Supabase client (for testing and reinitialization).
    """
    global _supabase_client, _supabase_admin_client
    _supabase_client = None
    _supabase_admin_client = None
    logger.info("🔄 Supabase client reset")
    return True


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


# ─── CHECK SUPABASE HEALTH ─────────────────────────────────────────

def check_supabase_health() -> Dict[str, Any]:
    """
    Check Supabase connection health.
    Returns a dictionary with health status.
    """
    try:
        client = get_supabase_client()
        # Simple query to test connection
        response = client.table('system_settings').select('*').limit(1).execute()
        return {
            'connected': True,
            'message': 'Supabase connection successful',
            'timestamp': datetime.now().isoformat(),
            'url': os.getenv("SUPABASE_URL", "not_set")
        }
    except Exception as e:
        logger.error(f"Supabase health check failed: {str(e)}")
        return {
            'connected': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'url': os.getenv("SUPABASE_URL", "not_set")
        }


# ─── GET STATS ──────────────────────────────────────────────────────

def get_stats() -> Dict[str, Any]:
    """
    Get database statistics.
    """
    try:
        client = get_supabase_client()
        
        # Count vehicles
        vehicles = client.table('vehicles').select('count', count='exact').execute()
        
        # Count valuations
        valuations = client.table('service_requests').select('count', count='exact').eq('service_type', 'valuation').execute()
        
        # Count inspections
        inspections = client.table('service_requests').select('count', count='exact').eq('service_type', 'inspection').execute()
        
        # Count users
        users = client.table('user_profiles').select('count', count='exact').execute()
        
        return {
            'vehicles': vehicles.count if hasattr(vehicles, 'count') else 0,
            'valuations': valuations.count if hasattr(valuations, 'count') else 0,
            'inspections': inspections.count if hasattr(inspections, 'count') else 0,
            'users': users.count if hasattr(users, 'count') else 0,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get stats error: {str(e)}")
        return {'error': str(e), 'timestamp': datetime.now().isoformat()}


# ─── VEHICLE FUNCTIONS ─────────────────────────────────────────────

def get_vehicle_by_vin(vin: str) -> list:
    """
    Get vehicle by VIN.
    """
    try:
        client = get_supabase_client()
        response = client.table('vehicles').select('*').eq('vin', vin.upper().strip()).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get vehicle by VIN error: {str(e)}")
        return []


def get_vehicles_by_user(user_id: str) -> list:
    """
    Get all vehicles for a user.
    """
    try:
        client = get_supabase_client()
        response = client.table('vehicles').select('*').eq('user_id', user_id).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get vehicles by user error: {str(e)}")
        return []


def create_vehicle(vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new vehicle.
    """
    try:
        client = get_supabase_client()
        vehicle_data['created_at'] = datetime.now().isoformat()
        vehicle_data['updated_at'] = datetime.now().isoformat()
        response = client.table('vehicles').insert(vehicle_data).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Failed to create vehicle'}
    except Exception as e:
        logger.error(f"Create vehicle error: {str(e)}")
        return {'success': False, 'error': str(e)}


# ─── SERVICE REQUEST FUNCTIONS ─────────────────────────────────────

def save_service_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a service request.
    """
    try:
        client = get_supabase_client()
        request_data['created_at'] = datetime.now().isoformat()
        request_data['updated_at'] = datetime.now().isoformat()
        response = client.table('service_requests').insert(request_data).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Failed to save service request'}
    except Exception as e:
        logger.error(f"Save service request error: {str(e)}")
        return {'success': False, 'error': str(e)}


def get_service_requests(user_id: str, service_type: str = None, limit: int = 50) -> list:
    """
    Get service requests for a user.
    """
    try:
        client = get_supabase_client()
        query = client.table('service_requests').select('*').eq('user_id', user_id)
        if service_type:
            query = query.eq('service_type', service_type)
        response = query.order('created_at', desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get service requests error: {str(e)}")
        return []


# ─── QUICK TEST ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing Supabase Client...")
    try:
        client = get_supabase_client()
        print("✅ Public client created successfully")
        
        if test_connection():
            print("✅ Connection test passed")
        else:
            print("❌ Connection test failed")
            
        health = check_supabase_health()
        print(f"✅ Health: {health.get('message', 'OK')}")
        
        print("✅ Supabase client test complete")
    except Exception as e:
        print(f"❌ Error: {e}")
