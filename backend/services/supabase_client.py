# services/supabase_client.py - Supabase Client (Production Ready)
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ─── Global Client Instances ──────────────────────────────────
_supabase_client = None
_supabase_admin_client = None

# ─── Main Client ──────────────────────────────────────────────

def get_supabase_client() -> Client:
    """
    Get Supabase client instance (singleton pattern)
    No proxy - simple and clean
    """
    global _supabase_client
    
    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url:
            raise ValueError("SUPABASE_URL environment variable is not set")
        if not supabase_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is not set")
        
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("✅ Supabase client initialized")
    
    return _supabase_client

# ─── Admin Client ─────────────────────────────────────────────

def get_supabase_admin() -> Optional[Client]:
    """
    Get Supabase admin client with service role
    """
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

# ─── Reset Client ─────────────────────────────────────────────

def reset_supabase_client():
    """
    Reset Supabase client (useful for testing)
    """
    global _supabase_client, _supabase_admin_client
    _supabase_client = None
    _supabase_admin_client = None
    logger.info("🔄 Supabase client reset")

# ─── Alias ─────────────────────────────────────────────────────

def get_supabase():
    """
    Alias for get_supabase_client()
    """
    return get_supabase_client()

# ─── Health Check ─────────────────────────────────────────────

def check_supabase_health() -> Dict[str, Any]:
    """
    Check Supabase connection health
    """
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

# ─── Vehicle Functions ─────────────────────────────────────────

def get_vehicle_by_vin(vin: str) -> List[Dict[str, Any]]:
    """
    Get vehicle by VIN
    """
    try:
        client = get_supabase_client()
        response = client.table('vehicles').select('*').eq('vin', vin.upper().strip()).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get vehicle by VIN error: {str(e)}")
        return []

def get_vehicles_by_user(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all vehicles for a user
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
    Create a new vehicle
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

def update_vehicle(vin: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing vehicle
    """
    try:
        client = get_supabase_client()
        update_data['updated_at'] = datetime.now().isoformat()
        response = client.table('vehicles').update(update_data).eq('vin', vin.upper().strip()).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Vehicle not found'}
    except Exception as e:
        logger.error(f"Update vehicle error: {str(e)}")
        return {'success': False, 'error': str(e)}

# ─── VIN Scan Functions ────────────────────────────────────────

def save_vin_scan(user_id: str, vin: str, image_url: str = None, status: str = 'pending') -> Dict[str, Any]:
    """
    Save a VIN scan record
    """
    try:
        client = get_supabase_client()
        data = {
            'user_id': user_id,
            'vin': vin.upper().strip(),
            'image_url': image_url,
            'status': status,
            'created_at': datetime.now().isoformat()
        }
        response = client.table('vin_scans').insert(data).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Failed to save VIN scan'}
    except Exception as e:
        logger.error(f"Save VIN scan error: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_vin_scans(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get VIN scans for a user
    """
    try:
        client = get_supabase_client()
        response = client.table('vin_scans').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get VIN scans error: {str(e)}")
        return []

# ─── Service Request Functions ─────────────────────────────────

def save_service_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a service request (valuation, inspection, assessment, etc.)
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

def get_service_requests(user_id: str, service_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get service requests for a user
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

def get_service_request(request_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a service request by ID
    """
    try:
        client = get_supabase_client()
        response = client.table('service_requests').select('*').eq('id', request_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get service request error: {str(e)}")
        return None

# ─── Payment/Transaction Functions ─────────────────────────────

def save_transaction(transaction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a transaction record
    """
    try:
        client = get_supabase_client()
        transaction_data['created_at'] = datetime.now().isoformat()
        response = client.table('transactions').insert(transaction_data).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Failed to save transaction'}
    except Exception as e:
        logger.error(f"Save transaction error: {str(e)}")
        return {'success': False, 'error': str(e)}

def update_transaction_status(checkout_request_id: str, status: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Update transaction status
    """
    try:
        client = get_supabase_client()
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        if data:
            update_data['payment_data'] = data
        
        response = client.table('transactions').update(update_data).eq('checkout_request_id', checkout_request_id).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Transaction not found'}
    except Exception as e:
        logger.error(f"Update transaction error: {str(e)}")
        return {'success': False, 'error': str(e)}

# ─── Statistics Functions ──────────────────────────────────────

def get_stats() -> Dict[str, Any]:
    """
    Get database statistics
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
        return {'error': str(e)}

# ─── System Settings Functions ─────────────────────────────────

def get_system_settings(keys: List[str] = None) -> Dict[str, Any]:
    """
    Get system settings
    """
    try:
        client = get_supabase_client()
        query = client.table('system_settings').select('setting_key, setting_value')
        if keys:
            query = query.in_('setting_key', keys)
        response = query.execute()
        
        settings = {}
        for row in response.data:
            settings[row['setting_key']] = row['setting_value']
        return settings
    except Exception as e:
        logger.error(f"Get system settings error: {str(e)}")
        return {}

def update_system_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update system settings
    """
    try:
        client = get_supabase_client()
        results = []
        for key, value in settings.items():
            response = client.table('system_settings').upsert({
                'setting_key': key,
                'setting_value': str(value),
                'updated_at': datetime.now().isoformat()
            }).execute()
            if response.data:
                results.append(response.data[0])
        
        return {'success': True, 'data': results}
    except Exception as e:
        logger.error(f"Update system settings error: {str(e)}")
        return {'success': False, 'error': str(e)}

# ─── Quick Test ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing Supabase Client...")
    
    try:
        # Test main client
        client = get_supabase_client()
        print("✅ Client created successfully")
        
        # Test health
        health = check_supabase_health()
        print(f"✅ Health: {health.get('message', 'OK')}")
        
        # Test stats
        stats = get_stats()
        print(f"✅ Stats: {stats}")
        
        print("✅ Supabase client test complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")
