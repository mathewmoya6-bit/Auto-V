"""
Supabase REST API Client - Direct HTTP calls (no supabase-py library)
Fully aligned with AUTO-V Platform
"""

import os
import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip('/')
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Use service role key if available, otherwise anon key
SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY


def get_supabase_headers() -> Dict[str, str]:
    """Get headers for Supabase REST API requests"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
    
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def supabase_request(method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
    """
    Make a request to Supabase REST API with full logging.
    
    Args:
        method: HTTP method (GET, POST, PATCH, DELETE)
        endpoint: API endpoint (e.g., "payments")
        data: Request body data for POST/PATCH
        params: Query parameters for GET requests
    
    Returns:
        Response data as dictionary
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = get_supabase_headers()
    
    # Log the request details
    logger.info(f"🔗 {method.upper()} {url}")
    if data:
        logger.info(f"📦 Request data: {data}")
    if params:
        logger.info(f"📦 Request params: {params}")
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        # Log response status
        logger.info(f"📨 Response status: {response.status_code}")
        
        if response.status_code in [200, 201, 204]:
            result = response.json() if response.text else {}
            logger.info(f"✅ Response data: {result}")
            return result
        else:
            error_msg = f"Supabase error: {response.status_code} - {response.text}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Supabase request failed: {e}", exc_info=True)
        raise Exception(f"Supabase request failed: {e}")


# ─── Payments CRUD ──────────────────────────────────────────

def create_payment(payment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a new payment record in Supabase.
    Returns the created record or None on error.
    """
    try:
        if "created_at" not in payment_data:
            payment_data["created_at"] = datetime.utcnow().isoformat()
        if "updated_at" not in payment_data:
            payment_data["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"📤 create_payment payload: {payment_data}")
        
        result = supabase_request("POST", "payments", payment_data)
        logger.info(f"📥 create_payment result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ create_payment error: {e}", exc_info=True)
        return None


def get_payment_by_payment_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by payment_id"""
    try:
        endpoint = f"payments?payment_id=eq.{payment_id}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_payment_by_payment_id error: {e}")
        return None


def get_payment_by_checkout_request_id(checkout_request_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by checkout_request_id"""
    try:
        endpoint = f"payments?checkout_request_id=eq.{checkout_request_id}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_payment_by_checkout_request_id error: {e}")
        return None


def get_payment_by_merchant_request_id(merchant_request_id: str) -> Optional[Dict[str, Any]]:
    """Get payment by merchant_request_id"""
    try:
        endpoint = f"payments?merchant_request_id=eq.{merchant_request_id}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_payment_by_merchant_request_id error: {e}")
        return None


def update_payment(payment_id: str, update_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Update payment by payment_id"""
    try:
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
        
        endpoint = f"payments?payment_id=eq.{payment_id}"
        result = supabase_request("PATCH", endpoint, update_data)
        return result
    except Exception as e:
        logger.error(f"update_payment error: {e}")
        return None


def update_payment_by_checkout_id(checkout_request_id: str, update_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Update payment by checkout_request_id"""
    try:
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
        
        endpoint = f"payments?checkout_request_id=eq.{checkout_request_id}"
        result = supabase_request("PATCH", endpoint, update_data)
        return result
    except Exception as e:
        logger.error(f"update_payment_by_checkout_id error: {e}")
        return None


def get_payment_status(payment_id: str) -> Optional[Dict[str, Any]]:
    """Get payment status by payment_id"""
    return get_payment_by_payment_id(payment_id)


def get_user_payments(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all payments for a user"""
    try:
        endpoint = f"payments?user_id=eq.{user_id}&order=created_at.desc&limit={limit}"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_user_payments error: {e}")
        return []


def get_all_payments(limit: int = 100) -> List[Dict[str, Any]]:
    """Get all payments"""
    try:
        endpoint = f"payments?order=created_at.desc&limit={limit}"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_all_payments error: {e}")
        return []


def get_pending_payments() -> List[Dict[str, Any]]:
    """Get all pending payments"""
    try:
        endpoint = "payments?status=eq.pending&order=created_at.desc"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_pending_payments error: {e}")
        return []


def delete_payment(payment_id: str) -> bool:
    """Delete a payment by payment_id"""
    try:
        endpoint = f"payments?payment_id=eq.{payment_id}"
        supabase_request("DELETE", endpoint)
        return True
    except Exception as e:
        logger.error(f"delete_payment error: {e}")
        return False


# ─── Vehicles CRUD ──────────────────────────────────────────

def create_vehicle(vehicle_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new vehicle record"""
    try:
        if "created_at" not in vehicle_data:
            vehicle_data["created_at"] = datetime.utcnow().isoformat()
        if "updated_at" not in vehicle_data:
            vehicle_data["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"📤 create_vehicle payload: {vehicle_data}")
        result = supabase_request("POST", "vehicles", vehicle_data)
        logger.info(f"📥 create_vehicle result: {result}")
        return result
    except Exception as e:
        logger.error(f"create_vehicle error: {e}", exc_info=True)
        return None


def get_vehicle_by_vin(vin: str) -> Optional[Dict[str, Any]]:
    """Get vehicle by VIN"""
    try:
        endpoint = f"vehicles?vin=eq.{vin.upper()}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_vehicle_by_vin error: {e}")
        return None


def get_vehicle_by_license_plate(license_plate: str) -> Optional[Dict[str, Any]]:
    """Get vehicle by license plate"""
    try:
        endpoint = f"vehicles?license_plate=eq.{license_plate.upper()}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_vehicle_by_license_plate error: {e}")
        return None


def get_user_vehicles(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all vehicles for a user"""
    try:
        endpoint = f"vehicles?user_id=eq.{user_id}&order=created_at.desc&limit={limit}"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_user_vehicles error: {e}")
        return []


def update_vehicle(vin: str, update_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Update vehicle by VIN"""
    try:
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
        
        endpoint = f"vehicles?vin=eq.{vin.upper()}"
        result = supabase_request("PATCH", endpoint, update_data)
        return result
    except Exception as e:
        logger.error(f"update_vehicle error: {e}")
        return None


# ─── Valuations CRUD ──────────────────────────────────────────

def create_valuation(valuation_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new valuation record"""
    try:
        if "created_at" not in valuation_data:
            valuation_data["created_at"] = datetime.utcnow().isoformat()
        if "updated_at" not in valuation_data:
            valuation_data["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"📤 create_valuation payload: {valuation_data}")
        result = supabase_request("POST", "valuations", valuation_data)
        logger.info(f"📥 create_valuation result: {result}")
        return result
    except Exception as e:
        logger.error(f"create_valuation error: {e}", exc_info=True)
        return None


def get_valuation_by_id(valuation_id: str) -> Optional[Dict[str, Any]]:
    """Get valuation by ID"""
    try:
        endpoint = f"valuations?id=eq.{valuation_id}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_valuation_by_id error: {e}")
        return None


def get_valuations_by_user(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all valuations for a user"""
    try:
        endpoint = f"valuations?user_id=eq.{user_id}&order=created_at.desc&limit={limit}"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_valuations_by_user error: {e}")
        return []


def get_valuations_by_vin(vin: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get valuations by VIN"""
    try:
        endpoint = f"valuations?vin=eq.{vin.upper()}&order=created_at.desc&limit={limit}"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_valuations_by_vin error: {e}")
        return []


# ─── Certificates CRUD ──────────────────────────────────────────

def create_certificate(certificate_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new certificate"""
    try:
        if "created_at" not in certificate_data:
            certificate_data["created_at"] = datetime.utcnow().isoformat()
        if "updated_at" not in certificate_data:
            certificate_data["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"📤 create_certificate payload: {certificate_data}")
        result = supabase_request("POST", "certificates", certificate_data)
        logger.info(f"📥 create_certificate result: {result}")
        return result
    except Exception as e:
        logger.error(f"create_certificate error: {e}", exc_info=True)
        return None


def get_certificate_by_number(certificate_number: str) -> Optional[Dict[str, Any]]:
    """Get certificate by certificate number"""
    try:
        endpoint = f"certificates?certificate_number=eq.{certificate_number}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_certificate_by_number error: {e}")
        return None


def get_user_certificates(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all certificates for a user"""
    try:
        endpoint = f"certificates?user_id=eq.{user_id}&order=issued_at.desc&limit={limit}"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_user_certificates error: {e}")
        return []


def update_certificate(certificate_number: str, update_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Update certificate by certificate number"""
    try:
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
        
        endpoint = f"certificates?certificate_number=eq.{certificate_number}"
        result = supabase_request("PATCH", endpoint, update_data)
        return result
    except Exception as e:
        logger.error(f"update_certificate error: {e}")
        return None


# ─── Service Requests CRUD ──────────────────────────────────

def create_service_request(request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new service request"""
    try:
        if "created_at" not in request_data:
            request_data["created_at"] = datetime.utcnow().isoformat()
        if "updated_at" not in request_data:
            request_data["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"📤 create_service_request payload: {request_data}")
        result = supabase_request("POST", "service_requests", request_data)
        logger.info(f"📥 create_service_request result: {result}")
        return result
    except Exception as e:
        logger.error(f"create_service_request error: {e}", exc_info=True)
        return None


def get_service_request_by_id(request_id: str) -> Optional[Dict[str, Any]]:
    """Get service request by ID"""
    try:
        endpoint = f"service_requests?id=eq.{request_id}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_service_request_by_id error: {e}")
        return None


def get_user_service_requests(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all service requests for a user"""
    try:
        endpoint = f"service_requests?user_id=eq.{user_id}&order=created_at.desc&limit={limit}"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_user_service_requests error: {e}")
        return []


def update_service_request(request_id: str, update_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Update service request by ID"""
    try:
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
        
        endpoint = f"service_requests?id=eq.{request_id}"
        result = supabase_request("PATCH", endpoint, update_data)
        return result
    except Exception as e:
        logger.error(f"update_service_request error: {e}")
        return None


# ─── Users CRUD ──────────────────────────────────────────────────

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    try:
        endpoint = f"users?id=eq.{user_id}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_user_by_id error: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    try:
        endpoint = f"users?email=eq.{email.lower()}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_user_by_email error: {e}")
        return None


def create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new user"""
    try:
        if "created_at" not in user_data:
            user_data["created_at"] = datetime.utcnow().isoformat()
        if "updated_at" not in user_data:
            user_data["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"📤 create_user payload: {user_data}")
        result = supabase_request("POST", "users", user_data)
        logger.info(f"📥 create_user result: {result}")
        return result
    except Exception as e:
        logger.error(f"create_user error: {e}", exc_info=True)
        return None


def update_user(user_id: str, update_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Update user by ID"""
    try:
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
        
        endpoint = f"users?id=eq.{user_id}"
        result = supabase_request("PATCH", endpoint, update_data)
        return result
    except Exception as e:
        logger.error(f"update_user error: {e}")
        return None


# ─── Test Functions ──────────────────────────────────────────

def test_connection() -> Dict[str, Any]:
    """Test Supabase connection"""
    try:
        result = get_all_payments(limit=1)
        return {
            "connected": True,
            "message": "Supabase connection successful",
            "payments_count": len(result)
        }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Supabase connection failed: {str(e)}"
        }


def test_payment_flow() -> Dict[str, Any]:
    """Test full payment flow"""
    try:
        # Create test payment
        test_payment = {
            "payment_id": f"TEST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "checkout_request_id": f"ws_CO_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "merchant_request_id": f"mreq_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "phone": "254712345678",
            "amount": 500.00,
            "reference": f"REF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "status": "pending",
            "user_id": "test-user-123"
        }
        
        created = create_payment(test_payment)
        if not created:
            return {"success": False, "error": "Failed to create test payment"}
        
        # Get payment
        retrieved = get_payment_by_payment_id(test_payment["payment_id"])
        if not retrieved:
            return {"success": False, "error": "Failed to retrieve test payment"}
        
        # Update payment
        updated = update_payment(test_payment["payment_id"], {"status": "completed"})
        if not updated:
            return {"success": False, "error": "Failed to update test payment"}
        
        return {
            "success": True,
            "message": "Payment flow test passed",
            "payment": retrieved
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ─── Compatibility Stub ─────────────────────────────────────

def get_supabase_client():
    """
    Compatibility function – REST version does not use a client.
    Provided to avoid ImportError in services/__init__.py.
    """
    return None
