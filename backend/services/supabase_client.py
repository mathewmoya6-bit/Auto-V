# services/supabase_client.py - Direct REST API calls (no supabase library)

import os
import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip('/')
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

def get_supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def supabase_request(method: str, endpoint: str, data: Dict = None) -> Dict:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = get_supabase_headers()
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        if response.status_code in [200, 201, 204]:
            return response.json() if response.text else {}
        else:
            raise Exception(f"Supabase error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Supabase request failed: {e}")

# ---- CRUD functions ----
def create_payment(payment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        if "created_at" not in payment_data:
            payment_data["created_at"] = datetime.utcnow().isoformat()
        return supabase_request("POST", "payments", payment_data)
    except Exception as e:
        logger.error(f"create_payment error: {e}")
        return None

def get_payment_by_payment_id(payment_id: str) -> Optional[Dict[str, Any]]:
    try:
        endpoint = f"payments?payment_id=eq.{payment_id}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_payment_by_payment_id error: {e}")
        return None

def get_payment_by_checkout_request_id(checkout_request_id: str) -> Optional[Dict[str, Any]]:
    try:
        endpoint = f"payments?checkout_request_id=eq.{checkout_request_id}&limit=1"
        result = supabase_request("GET", endpoint)
        return result[0] if result else None
    except Exception as e:
        logger.error(f"get_payment_by_checkout_request_id error: {e}")
        return None

def update_payment_status(payment_id: str, update_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    try:
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
        endpoint = f"payments?payment_id=eq.{payment_id}"
        return supabase_request("PATCH", endpoint, update_data)
    except Exception as e:
        logger.error(f"update_payment_status error: {e}")
        return None

def get_payment_status(payment_id: str) -> Optional[Dict[str, Any]]:
    return get_payment_by_payment_id(payment_id)

def get_user_payments(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        endpoint = f"payments?user_id=eq.{user_id}&order=created_at.desc&limit={limit}"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_user_payments error: {e}")
        return []

def get_all_payments(limit: int = 100) -> List[Dict[str, Any]]:
    try:
        endpoint = f"payments?order=created_at.desc&limit={limit}"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_all_payments error: {e}")
        return []

def get_pending_payments() -> List[Dict[str, Any]]:
    try:
        endpoint = "payments?status=eq.pending&order=created_at.desc"
        result = supabase_request("GET", endpoint)
        return result if result else []
    except Exception as e:
        logger.error(f"get_pending_payments error: {e}")
        return []

def delete_payment(payment_id: str) -> bool:
    try:
        endpoint = f"payments?payment_id=eq.{payment_id}"
        supabase_request("DELETE", endpoint)
        return True
    except Exception as e:
        logger.error(f"delete_payment error: {e}")
        return False

def test_connection() -> Dict[str, Any]:
    try:
        result = get_all_payments(limit=1)
        return {"connected": True, "message": "Supabase connection successful", "payments_count": len(result)}
    except Exception as e:
        return {"connected": False, "message": f"Supabase connection failed: {str(e)}"}

# ---- Compatibility stub for old imports ----
def get_supabase_client():
    """
    Compatibility function – REST version does not use a client.
    Provided to avoid ImportError in services/__init__.py.
    """
    return None
