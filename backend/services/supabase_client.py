# supabase.py - Supabase Client for AUTO-V
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_ROLE = os.getenv('SUPABASE_SERVICE_ROLE', '')

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable is not set")
if not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_ANON_KEY environment variable is not set")

# ─── Global Clients ─────────────────────────────────────────────

_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None

# ─── Main Client ──────────────────────────────────────────────

def get_client() -> Client:
    """
    Get Supabase client instance (singleton pattern).
    
    Returns:
        Client: Supabase client instance
    
    Raises:
        ValueError: If credentials are not set
    """
    global _supabase_client
    
    if _supabase_client is None:
        logger.info(f"🔌 Initializing Supabase client for: {SUPABASE_URL}")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("✅ Supabase client initialized successfully")
    
    return _supabase_client

def get_admin_client() -> Optional[Client]:
    """
    Get Supabase admin client with service role.
    
    Returns:
        Optional[Client]: Admin client instance or None
    """
    global _supabase_admin_client
    
    if _supabase_admin_client is None and SUPABASE_SERVICE_ROLE:
        logger.info("🔌 Initializing Supabase admin client")
        _supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
        logger.info("✅ Supabase admin client initialized")
    
    return _supabase_admin_client

def reset_client():
    """Reset the Supabase client (useful for testing)."""
    global _supabase_client, _supabase_admin_client
    _supabase_client = None
    _supabase_admin_client = None
    logger.info("🔄 Supabase client reset")

# ─── Alias ─────────────────────────────────────────────────────

def get_supabase() -> Client:
    """Alias for get_client()."""
    return get_client()

# ─── Health Check ─────────────────────────────────────────────

def check_health() -> Dict[str, Any]:
    """
    Check Supabase connection health.
    
    Returns:
        Dict with health status
    """
    try:
        client = get_client()
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

# ─── Vehicles ──────────────────────────────────────────────────

def get_vehicle_by_vin(vin: str) -> List[Dict[str, Any]]:
    """
    Get vehicle by VIN.
    
    Args:
        vin: Vehicle Identification Number
        
    Returns:
        List of vehicle records (should be 0 or 1)
    """
    try:
        client = get_client()
        response = client.table('vehicles').select('*').eq('vin', vin.upper().strip()).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get vehicle by VIN error: {str(e)}")
        return []

def get_vehicles_by_user(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all vehicles for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        List of vehicle records
    """
    try:
        client = get_client()
        response = client.table('vehicles').select('*').eq('user_id', user_id).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get vehicles by user error: {str(e)}")
        return []

def create_vehicle(vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new vehicle record.
    
    Args:
        vehicle_data: Vehicle data
        
    Returns:
        Dict with success status and vehicle data
    """
    try:
        client = get_client()
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
    Update an existing vehicle.
    
    Args:
        vin: Vehicle Identification Number
        update_data: Data to update
        
    Returns:
        Dict with success status and vehicle data
    """
    try:
        client = get_client()
        update_data['updated_at'] = datetime.now().isoformat()
        response = client.table('vehicles').update(update_data).eq('vin', vin.upper().strip()).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Vehicle not found'}
    except Exception as e:
        logger.error(f"Update vehicle error: {str(e)}")
        return {'success': False, 'error': str(e)}

def delete_vehicle(vin: str) -> Dict[str, Any]:
    """
    Delete a vehicle.
    
    Args:
        vin: Vehicle Identification Number
        
    Returns:
        Dict with success status
    """
    try:
        client = get_client()
        response = client.table('vehicles').delete().eq('vin', vin.upper().strip()).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Vehicle not found'}
    except Exception as e:
        logger.error(f"Delete vehicle error: {str(e)}")
        return {'success': False, 'error': str(e)}

# ─── Vehicle Images ───────────────────────────────────────────

def save_vehicle_image(vin: str, slot: str, image_url: str) -> Dict[str, Any]:
    """
    Save vehicle image URL.
    
    Args:
        vin: Vehicle Identification Number
        slot: Image slot (front, rear, left, etc.)
        image_url: URL of the image
        
    Returns:
        Dict with success status and image data
    """
    try:
        client = get_client()
        data = {
            'vin': vin.upper().strip(),
            'slot': slot,
            'image_url': image_url,
            'uploaded_at': datetime.now().isoformat()
        }
        response = client.table('vehicle_images').insert(data).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Failed to save image'}
    except Exception as e:
        logger.error(f"Save vehicle image error: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_vehicle_images(vin: str) -> List[Dict[str, Any]]:
    """
    Get all images for a vehicle.
    
    Args:
        vin: Vehicle Identification Number
        
    Returns:
        List of image records
    """
    try:
        client = get_client()
        response = client.table('vehicle_images').select('*').eq('vin', vin.upper().strip()).order('order_index').execute()
        return response.data
    except Exception as e:
        logger.error(f"Get vehicle images error: {str(e)}")
        return []

# ─── VIN Scans ─────────────────────────────────────────────────

def save_vin_scan(user_id: str, vin: str, image_url: str = None, status: str = 'pending') -> Dict[str, Any]:
    """
    Save a VIN scan record.
    
    Args:
        user_id: User ID
        vin: VIN number
        image_url: Image URL (optional)
        status: Scan status (pending, verified, invalid)
        
    Returns:
        Dict with success status and scan data
    """
    try:
        client = get_client()
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
    Get VIN scans for a user.
    
    Args:
        user_id: User ID
        limit: Maximum number of records
        
    Returns:
        List of scan records
    """
    try:
        client = get_client()
        response = client.table('vin_scans').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Get VIN scans error: {str(e)}")
        return []

# ─── Service Requests ──────────────────────────────────────────

def save_service_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a service request.
    
    Args:
        request_data: Service request data
        
    Returns:
        Dict with success status and request data
    """
    try:
        client = get_client()
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
    Get service requests for a user.
    
    Args:
        user_id: User ID
        service_type: Filter by service type (optional)
        limit: Maximum number of records
        
    Returns:
        List of service request records
    """
    try:
        client = get_client()
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
    Get a service request by ID.
    
    Args:
        request_id: Request ID
        
    Returns:
        Service request record or None
    """
    try:
        client = get_client()
        response = client.table('service_requests').select('*').eq('id', request_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get service request error: {str(e)}")
        return None

def update_service_request(request_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a service request.
    
    Args:
        request_id: Request ID
        update_data: Data to update
        
    Returns:
        Dict with success status and request data
    """
    try:
        client = get_client()
        update_data['updated_at'] = datetime.now().isoformat()
        response = client.table('service_requests').update(update_data).eq('id', request_id).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Request not found'}
    except Exception as e:
        logger.error(f"Update service request error: {str(e)}")
        return {'success': False, 'error': str(e)}

# ─── Transactions (M-Pesa) ─────────────────────────────────────

def save_transaction(transaction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a transaction record.
    
    Args:
        transaction_data: Transaction data
        
    Returns:
        Dict with success status and transaction data
    """
    try:
        client = get_client()
        transaction_data['created_at'] = datetime.now().isoformat()
        response = client.table('transactions').insert(transaction_data).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Failed to save transaction'}
    except Exception as e:
        logger.error(f"Save transaction error: {str(e)}")
        return {'success': False, 'error': str(e)}

def update_transaction_status(checkout_request_id: str, status: str, payment_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Update transaction status.
    
    Args:
        checkout_request_id: Checkout request ID
        status: New status (pending, completed, failed)
        payment_data: Payment data (optional)
        
    Returns:
        Dict with success status and transaction data
    """
    try:
        client = get_client()
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        if payment_data:
            update_data['payment_data'] = payment_data
        
        response = client.table('transactions').update(update_data).eq('checkout_request_id', checkout_request_id).execute()
        if response.data:
            return {'success': True, 'data': response.data[0]}
        return {'success': False, 'error': 'Transaction not found'}
    except Exception as e:
        logger.error(f"Update transaction error: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_transaction(checkout_request_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a transaction by checkout request ID.
    
    Args:
        checkout_request_id: Checkout request ID
        
    Returns:
        Transaction record or None
    """
    try:
        client = get_client()
        response = client.table('transactions').select('*').eq('checkout_request_id', checkout_request_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Get transaction error: {str(e)}")
        return None

# ─── System Settings ───────────────────────────────────────────

def get_system_settings(keys: List[str] = None) -> Dict[str, Any]:
    """
    Get system settings.
    
    Args:
        keys: List of setting keys to retrieve (optional)
        
    Returns:
        Dict of settings
    """
    try:
        client = get_client()
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
    Update system settings.
    
    Args:
        settings: Dict of settings to update
        
    Returns:
        Dict with success status
    """
    try:
        client = get_client()
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

# ─── Statistics ─────────────────────────────────────────────────

def get_stats() -> Dict[str, Any]:
    """
    Get database statistics.
    
    Returns:
        Dict with statistics
    """
    try:
        client = get_client()
        
        # Count vehicles
        vehicles = client.table('vehicles').select('count', count='exact').execute()
        
        # Count valuations
        valuations = client.table('service_requests').select('count', count='exact').eq('service_type', 'valuation').execute()
        
        # Count inspections
        inspections = client.table('service_requests').select('count', count='exact').eq('service_type', 'inspection').execute()
        
        # Count users (try different table names)
        users = 0
        try:
            users_resp = client.table('user_profiles').select('count', count='exact').execute()
            users = users_resp.count if hasattr(users_resp, 'count') else 0
        except:
            try:
                users_resp = client.table('users').select('count', count='exact').execute()
                users = users_resp.count if hasattr(users_resp, 'count') else 0
            except:
                pass
        
        return {
            'vehicles': vehicles.count if hasattr(vehicles, 'count') else 0,
            'valuations': valuations.count if hasattr(valuations, 'count') else 0,
            'inspections': inspections.count if hasattr(inspections, 'count') else 0,
            'users': users,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get stats error: {str(e)}")
        return {'error': str(e)}

# ─── Quick Test ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing Supabase Client...")
    
    try:
        # Test connection
        client = get_client()
        print("✅ Client created successfully")
        
        # Test health
        health = check_health()
        print(f"✅ Health: {health.get('message', 'OK')}")
        
        # Test stats
        stats = get_stats()
        print(f"✅ Stats: {stats}")
        
        print("✅ Supabase client test complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")
