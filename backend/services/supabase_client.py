# services/supabase_client.py
import os
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import wraps
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

logger = logging.getLogger(__name__)

# ─── DECORATORS ──────────────────────────────────────────────

def retry_on_failure(max_retries=3, delay=1, backoff=2):
    """Retry decorator for Supabase operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Max retries reached for {func.__name__}: {str(e)}")
                        raise
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__}: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator

# ─── SUPABASE CLIENT ──────────────────────────────────────────

class SupabaseClient:
    """Enhanced Supabase client with connection pooling, caching, and retry logic"""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._admin_client: Optional[Client] = None
        self._initialized = False
        self._last_connection_check = None
        self._connection_status = False
        self._cache = {}
        
        # Get credentials from environment
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.service_role = os.getenv("SUPABASE_SERVICE_ROLE")
        
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL environment variable is not set")
        if not self.supabase_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is not set")
        
        # Initialize immediately
        self._init_client()
    
    def _init_client(self):
        """Initialize the Supabase client with proper configuration"""
        try:
            # Create client with options
            client_options = ClientOptions(
                schema='public',
                headers={
                    'X-Client-Info': 'auto-v-backend',
                    'Cache-Control': 'no-cache'
                }
            )
            
            # Initialize client
            self._client = create_client(
                self.supabase_url, 
                self.supabase_key,
                options=client_options
            )
            
            # Initialize admin client if service role is available
            if self.service_role:
                self._admin_client = create_client(
                    self.supabase_url,
                    self.service_role,
                    options=client_options
                )
                logger.info("✅ Admin client initialized with service role")
            
            self._initialized = True
            self._connection_status = True
            self._last_connection_check = datetime.now()
            
            logger.info(f"✅ Supabase client initialized for: {self.supabase_url}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {str(e)}")
            raise
    
    # ─── CLIENT ACCESSORS ──────────────────────────────────────
    
    def get_client(self) -> Client:
        """Get the regular Supabase client"""
        return self._client
    
    def get_admin_client(self) -> Optional[Client]:
        """Get the admin client (with service role)"""
        return self._admin_client
    
    def get_table(self, table_name: str):
        """Get a table reference with proper error handling"""
        try:
            return self._client.table(table_name)
        except Exception as e:
            logger.error(f"Failed to get table {table_name}: {str(e)}")
            raise
    
    def get_storage(self, bucket_name: str):
        """Get a storage bucket reference"""
        try:
            return self._client.storage.from_(bucket_name)
        except Exception as e:
            logger.error(f"Failed to get storage bucket {bucket_name}: {str(e)}")
            raise
    
    def get_auth(self):
        """Get the auth client"""
        try:
            return self._client.auth
        except Exception as e:
            logger.error(f"Failed to get auth client: {str(e)}")
            raise

    # ─── USERS & AUTH ──────────────────────────────────────────

    @retry_on_failure(max_retries=3)
    def register_user(self, email: str, password: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Register a new user"""
        try:
            response = self._client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": metadata or {}}
            })
            
            if response.user:
                return {
                    "success": True,
                    "user_id": response.user.id,
                    "user": response.user
                }
            return {"success": False, "error": "Registration failed"}
        except Exception as e:
            logger.error(f"Register error: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_failure(max_retries=3)
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login user"""
        try:
            response = self._client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                return {
                    "success": True,
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "user": response.user
                }
            return {"success": False, "error": "Login failed"}
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_failure(max_retries=3)
    def logout_user(self) -> Dict[str, Any]:
        """Logout user"""
        try:
            self._client.auth.sign_out()
            return {"success": True}
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_failure(max_retries=3)
    def get_current_user(self) -> Dict[str, Any]:
        """Get current user"""
        try:
            response = self._client.auth.get_user()
            if response.user:
                return {
                    "success": True,
                    "user": response.user
                }
            return {"success": False, "error": "Not authenticated"}
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_failure(max_retries=3)
    def reset_password(self, email: str) -> Dict[str, Any]:
        """Request password reset"""
        try:
            self._client.auth.reset_password_for_email(email)
            return {"success": True, "message": "Password reset email sent"}
        except Exception as e:
            logger.error(f"Reset password error: {str(e)}")
            return {"success": False, "error": str(e)}

    # ─── VEHICLES ──────────────────────────────────────────────

    @retry_on_failure(max_retries=3)
    def get_vehicle_by_vin(self, vin: str) -> List[Dict[str, Any]]:
        """Get vehicle by VIN"""
        try:
            response = self._client.table("vehicles") \
                .select("*") \
                .eq("vin", vin) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Get vehicle by VIN error: {str(e)}")
            return []

    @retry_on_failure(max_retries=3)
    def get_vehicle_by_id(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Get vehicle by ID"""
        try:
            response = self._client.table("vehicles") \
                .select("*") \
                .eq("id", vehicle_id) \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Get vehicle by ID error: {str(e)}")
            return None

    @retry_on_failure(max_retries=3)
    def get_all_vehicles(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all vehicles with pagination"""
        try:
            response = self._client.table("vehicles") \
                .select("*") \
                .range(offset, offset + limit - 1) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Get all vehicles error: {str(e)}")
            return []

    @retry_on_failure(max_retries=3)
    def search_vehicles(self, query: str) -> List[Dict[str, Any]]:
        """Search vehicles by make, model, or year"""
        try:
            response = self._client.table("vehicles") \
                .select("*") \
                .or_(f"make.ilike.%{query}%,model.ilike.%{query}%,year::text.ilike.%{query}%") \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Search vehicles error: {str(e)}")
            return []

    @retry_on_failure(max_retries=3)
    def create_vehicle(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vehicle record"""
        try:
            vehicle_data["created_at"] = datetime.now().isoformat()
            vehicle_data["updated_at"] = datetime.now().isoformat()
            
            response = self._client.table("vehicles") \
                .insert(vehicle_data) \
                .execute()
            
            if response.data:
                return {"success": True, "vehicle": response.data[0]}
            return {"success": False, "error": "Failed to create vehicle"}
        except Exception as e:
            logger.error(f"Create vehicle error: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_failure(max_retries=3)
    def update_vehicle(self, vin: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing vehicle"""
        try:
            update_data["updated_at"] = datetime.now().isoformat()
            
            response = self._client.table("vehicles") \
                .update(update_data) \
                .eq("vin", vin) \
                .execute()
            
            if response.data:
                return {"success": True, "vehicle": response.data[0]}
            return {"success": False, "error": "Vehicle not found"}
        except Exception as e:
            logger.error(f"Update vehicle error: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_failure(max_retries=3)
    def delete_vehicle(self, vin: str) -> Dict[str, Any]:
        """Delete a vehicle"""
        try:
            response = self._client.table("vehicles") \
                .delete() \
                .eq("vin", vin) \
                .execute()
            
            if response.data:
                return {"success": True, "vehicle": response.data[0]}
            return {"success": False, "error": "Vehicle not found"}
        except Exception as e:
            logger.error(f"Delete vehicle error: {str(e)}")
            return {"success": False, "error": str(e)}

    # ─── VEHICLE IMAGES ────────────────────────────────────────

    @retry_on_failure(max_retries=3)
    def save_vehicle_image(self, vin: str, slot: str, image_url: str) -> Dict[str, Any]:
        """Save vehicle image URL"""
        try:
            data = {
                "vin": vin,
                "slot": slot,
                "image_url": image_url,
                "uploaded_at": datetime.now().isoformat()
            }
            
            response = self._client.table("vehicle_images") \
                .insert(data) \
                .execute()
            
            if response.data:
                return {"success": True, "image": response.data[0]}
            return {"success": False, "error": "Failed to save image"}
        except Exception as e:
            logger.error(f"Save vehicle image error: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_failure(max_retries=3)
    def get_vehicle_images(self, vin: str) -> List[Dict[str, Any]]:
        """Get all images for a vehicle"""
        try:
            response = self._client.table("vehicle_images") \
                .select("*") \
                .eq("vin", vin) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Get vehicle images error: {str(e)}")
            return []

    @retry_on_failure(max_retries=3)
    def delete_vehicle_image(self, image_id: str) -> Dict[str, Any]:
        """Delete a vehicle image"""
        try:
            response = self._client.table("vehicle_images") \
                .delete() \
                .eq("id", image_id) \
                .execute()
            
            if response.data:
                return {"success": True, "image": response.data[0]}
            return {"success": False, "error": "Image not found"}
        except Exception as e:
            logger.error(f"Delete vehicle image error: {str(e)}")
            return {"success": False, "error": str(e)}

    # ─── VIN SCANS ─────────────────────────────────────────────

    @retry_on_failure(max_retries=3)
    def save_vin_scan(self, user_id: str, vin: str, image_url: str, status: str = "pending") -> Dict[str, Any]:
        """Save VIN scan record"""
        try:
            data = {
                "user_id": user_id,
                "vin": vin,
                "image_url": image_url,
                "status": status,
                "scanned_at": datetime.now().isoformat()
            }
            
            response = self._client.table("vin_scans") \
                .insert(data) \
                .execute()
            
            if response.data:
                return {"success": True, "scan": response.data[0]}
            return {"success": False, "error": "Failed to save scan"}
        except Exception as e:
            logger.error(f"Save VIN scan error: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_failure(max_retries=3)
    def get_vin_scans(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get VIN scan history for a user"""
        try:
            response = self._client.table("vin_scans") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("scanned_at", desc=True) \
                .limit(limit) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Get VIN scans error: {str(e)}")
            return []

    @retry_on_failure(max_retries=3)
    def get_vin_scan_by_id(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get VIN scan by ID"""
        try:
            response = self._client.table("vin_scans") \
                .select("*") \
                .eq("id", scan_id) \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Get VIN scan by ID error: {str(e)}")
            return None

    @retry_on_failure(max_retries=3)
    def update_vin_scan_status(self, scan_id: str, status: str) -> Dict[str, Any]:
        """Update VIN scan status"""
        try:
            response = self._client.table("vin_scans") \
                .update({"status": status, "updated_at": datetime.now().isoformat()}) \
                .eq("id", scan_id) \
                .execute()
            
            if response.data:
                return {"success": True, "scan": response.data[0]}
            return {"success": False, "error": "Scan not found"}
        except Exception as e:
            logger.error(f"Update VIN scan status error: {str(e)}")
            return {"success": False, "error": str(e)}

    # ─── VALUATIONS ────────────────────────────────────────────

    @retry_on_failure(max_retries=3)
    def save_valuation(self, valuation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save valuation record"""
        try:
            valuation_data["created_at"] = datetime.now().isoformat()
            
            response = self._client.table("valuations") \
                .insert(valuation_data) \
                .execute()
            
            if response.data:
                return {"success": True, "valuation": response.data[0]}
            return {"success": False, "error": "Failed to save valuation"}
        except Exception as e:
            logger.error(f"Save valuation error: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_failure(max_retries=3)
    def get_valuation(self, valuation_id: str) -> Optional[Dict[str, Any]]:
        """Get valuation by ID"""
        try:
            response = self._client.table("valuations") \
                .select("*") \
                .eq("id", valuation_id) \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Get valuation error: {str(e)}")
            return None

    @retry_on_failure(max_retries=3)
    def get_valuations_by_vin(self, vin: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all valuations for a vehicle"""
        try:
            response = self._client.table("valuations") \
                .select("*") \
                .eq("vin", vin) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Get valuations by VIN error: {str(e)}")
            return []

    # ─── INSPECTIONS ───────────────────────────────────────────

    @retry_on_failure(max_retries=3)
    def save_inspection(self, inspection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save inspection record"""
        try:
            inspection_data["created_at"] = datetime.now().isoformat()
            inspection_data["updated_at"] = datetime.now().isoformat()
            
            response = self._client.table("inspections") \
                .insert(inspection_data) \
                .execute()
            
            if response.data:
                return {"success": True, "inspection": response.data[0]}
            return {"success": False, "error": "Failed to save inspection"}
        except Exception as e:
            logger.error(f"Save inspection error: {str(e)}")
            return {"success": False, "error": str(e)}

    @retry_on_failure(max_retries=3)
    def get_inspection(self, inspection_id: str) -> Optional[Dict[str, Any]]:
        """Get inspection by ID"""
        try:
            response = self._client.table("inspections") \
                .select("*") \
                .eq("id", inspection_id) \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Get inspection error: {str(e)}")
            return None

    @retry_on_failure(max_retries=3)
    def get_inspections_by_vin(self, vin: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all inspections for a vehicle"""
        try:
            response = self._client.table("inspections") \
                .select("*") \
                .eq("vin", vin) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Get inspections by VIN error: {str(e)}")
            return []

    # ─── STORAGE (File Upload) ─────────────────────────────────

    @retry_on_failure(max_retries=3)
    def upload_file(self, file_data: bytes, path: str, bucket: str = "uploads") -> str:
        """Upload file to Supabase storage"""
        try:
            response = self._client.storage.from_(bucket).upload(path, file_data)
            if response:
                url = self._client.storage.from_(bucket).get_public_url(path)
                return url
            raise Exception("Upload failed")
        except Exception as e:
            logger.error(f"Upload file error: {str(e)}")
            raise

    @retry_on_failure(max_retries=3)
    def delete_file(self, path: str, bucket: str = "uploads") -> bool:
        """Delete file from Supabase storage"""
        try:
            self._client.storage.from_(bucket).remove([path])
            return True
        except Exception as e:
            logger.error(f"Delete file error: {str(e)}")
            return False

    @retry_on_failure(max_retries=3)
    def list_files(self, bucket: str = "uploads", prefix: str = "") -> List[Dict[str, Any]]:
        """List files in a bucket"""
        try:
            response = self._client.storage.from_(bucket).list(prefix)
            return response
        except Exception as e:
            logger.error(f"List files error: {str(e)}")
            return []

    # ─── SYSTEM ─────────────────────────────────────────────────

    @retry_on_failure(max_retries=3)
    def check_health(self) -> Dict[str, Any]:
        """Check connection to Supabase"""
        try:
            response = self._client.table("system_settings") \
                .select("*") \
                .limit(1) \
                .execute()
            
            self._connection_status = True
            self._last_connection_check = datetime.now()
            
            return {
                "connected": True,
                "message": "Supabase connection successful",
                "timestamp": self._last_connection_check.isoformat()
            }
        except Exception as e:
            self._connection_status = False
            logger.error(f"Health check error: {str(e)}")
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    @retry_on_failure(max_retries=3)
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            # Get counts using admin client if available
            if self._admin_client:
                users = self._admin_client.auth.admin.list_users()
                user_count = len(users) if users else 0
            else:
                user_count = 0
            
            vehicles = self._client.table("vehicles").select("count", count="exact").execute()
            valuations = self._client.table("valuations").select("count", count="exact").execute()
            
            return {
                "vehicles": vehicles.count if hasattr(vehicles, 'count') else 0,
                "valuations": valuations.count if hasattr(valuations, 'count') else 0,
                "users": user_count,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Get stats error: {str(e)}")
            return {"error": str(e)}

    # ─── CACHE ──────────────────────────────────────────────────

    def query_with_cache(self, query_key: str, query_func, ttl: int = 300):
        """Execute a query with caching"""
        cache_key = f"query_cache_{query_key}"
        
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            if hasattr(cached_result, '_cache_time'):
                if (datetime.now() - cached_result._cache_time).seconds < ttl:
                    logger.debug(f"✅ Cache hit for: {query_key}")
                    return cached_result
        
        result = query_func()
        self._cache[cache_key] = result
        result._cache_time = datetime.now()
        return result

    def clear_cache(self):
        """Clear all cached queries"""
        self._cache.clear()
        logger.info("✅ Query cache cleared")

    def reset(self):
        """Reset the client (useful for testing)"""
        self._client = None
        self._admin_client = None
        self._initialized = False
        self._connection_status = False
        self._last_connection_check = None
        self._cache.clear()
        logger.info("🔄 Supabase client reset")

# ─── SINGLETON INSTANCE ──────────────────────────────────────

_supabase_instance = None

def get_supabase() -> SupabaseClient:
    """Get Supabase client instance (singleton pattern)"""
    global _supabase_instance
    
    if _supabase_instance is None:
        _supabase_instance = SupabaseClient()
    
    return _supabase_instance

def get_supabase_client() -> Client:
    """Get the raw Supabase client (for backward compatibility)"""
    return get_supabase().get_client()

def get_supabase_admin() -> Optional[Client]:
    """Get the admin client (with service role)"""
    return get_supabase().get_admin_client()

def reset_supabase_client():
    """Reset the Supabase client instance"""
    global _supabase_instance
    if _supabase_instance:
        _supabase_instance.reset()
    _supabase_instance = None
    logger.info("🔄 Supabase client reset")

# ─── CONVENIENCE FUNCTIONS ────────────────────────────────────

def get_vehicle_by_vin(vin: str) -> List[Dict[str, Any]]:
    """Convenience function to get vehicle by VIN"""
    return get_supabase().get_vehicle_by_vin(vin)

def save_vin_scan(user_id: str, vin: str, image_url: str, status: str = "pending") -> Dict[str, Any]:
    """Convenience function to save VIN scan"""
    return get_supabase().save_vin_scan(user_id, vin, image_url, status)

def check_supabase_health() -> Dict[str, Any]:
    """Convenience function to check Supabase health"""
    return get_supabase().check_health()

# ─── QUICK TEST ──────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing Supabase Client...")
    
    try:
        # Get client
        supabase = get_supabase()
        client = supabase.get_client()
        print("✅ Client initialized")
        
        # Test health
        health = supabase.check_health()
        print(f"✅ Health: {health['message']}")
        
        # Test query
        vehicles = supabase.get_all_vehicles(limit=5)
        print(f"✅ Found {len(vehicles)} vehicles")
        
        print("✅ Supabase Client test complete")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
