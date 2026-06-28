# services/carapi_service.py
import os
import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class CarAPIService:
    """
    CarAPI.dev integration service
    Documentation: https://carapi.dev/docs
    """
    
    def __init__(self):
        self.api_key = os.getenv('CARAPI_KEY', 'carapi_45747df211066bb9d14224ae998de7e7')
        self.base_url = "https://api.carapi.dev/v1"
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        if not self.api_key:
            logger.warning("⚠️ CARAPI_KEY not set. Vehicle data features will be limited.")
    
    def _get_cache_key(self, *args):
        return "_".join(str(arg) for arg in args)
    
    def _is_cache_valid(self, key):
        if key in self.cache:
            cached_time, _ = self.cache[key]
            return datetime.now() - cached_time < timedelta(seconds=self.cache_ttl)
        return False
    
    def _get_from_cache(self, key):
        if self._is_cache_valid(key):
            return self.cache[key][1]
        return None
    
    def _set_cache(self, key, data):
        self.cache[key] = (datetime.now(), data)
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Make authenticated request to CarAPI"""
        if not self.api_key:
            return {"error": "CARAPI_KEY not configured"}
        
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params['token'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"CarAPI request error: {e}")
            return {"error": str(e)}
    
    # ─── VIN DECODE ──────────────────────────────────────────────
    
    def decode_vin(self, vin: str) -> Dict[str, Any]:
        """
        Decode VIN to get vehicle specifications
        
        Args:
            vin: 17-character VIN number
            
        Returns:
            Vehicle specifications including make, model, year, engine, etc.
        """
        vin = vin.upper().strip()
        cache_key = self._get_cache_key("vin", vin)
        
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = self._make_request(f"vin-decode/{vin}")
        
        if "error" not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # ─── VEHICLE VALUATION ──────────────────────────────────────
    
    def get_valuation(self, vin: str) -> Dict[str, Any]:
        """
        Get vehicle market valuation
        
        Args:
            vin: 17-character VIN number
            
        Returns:
            Vehicle valuation including current value and depreciation
        """
        vin = vin.upper().strip()
        cache_key = self._get_cache_key("valuation", vin)
        
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = self._make_request("vehicle-valuation", {"vin": vin})
        
        if "error" not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # ─── PLATE TO VIN ────────────────────────────────────────────
    
    def plate_to_vin(self, plate: str, country: str = "us") -> Dict[str, Any]:
        """
        Convert license plate to VIN
        
        Args:
            plate: License plate number
            country: Country code (us, uk, de, etc.)
            
        Returns:
            VIN and vehicle details
        """
        cache_key = self._get_cache_key("plate", plate, country)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = self._make_request("plate-to-vin", {
            "plate": plate,
            "country": country
        })
        
        if "error" not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # ─── VEHICLE LISTING ─────────────────────────────────────────
    
    def search_vehicles(self, make: str = None, model: str = None, year: int = None) -> Dict[str, Any]:
        """
        Search for vehicle listings
        
        Args:
            make: Vehicle make (e.g., Toyota)
            model: Vehicle model (e.g., Corolla)
            year: Model year
            
        Returns:
            List of matching vehicles
        """
        params = {}
        if make:
            params['make'] = make
        if model:
            params['model'] = model
        if year:
            params['year'] = year
        
        cache_key = self._get_cache_key("search", make, model, year)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = self._make_request("vehicle-listing", params)
        
        if "error" not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # ─── VEHICLE PHOTOS ──────────────────────────────────────────
    
    def get_vehicle_photos(self, make: str, model: str, year: int) -> Dict[str, Any]:
        """
        Get vehicle photos
        
        Args:
            make: Vehicle make
            model: Vehicle model
            year: Model year
            
        Returns:
            Vehicle photos and galleries
        """
        cache_key = self._get_cache_key("photos", make, model, year)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = self._make_request("vehicle-photos", {
            "make": make,
            "model": model,
            "year": year
        })
        
        if "error" not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # ─── MILEAGE HISTORY ────────────────────────────────────────
    
    def get_mileage_history(self, vin: str) -> Dict[str, Any]:
        """
        Get vehicle mileage history
        
        Args:
            vin: 17-character VIN number
            
        Returns:
            Mileage records and history
        """
        vin = vin.upper().strip()
        cache_key = self._get_cache_key("mileage", vin)
        
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = self._make_request("mileage-history", {"vin": vin})
        
        if "error" not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # ─── VIN OCR ──────────────────────────────────────────────────
    
    def extract_vin_from_image(self, image_url: str) -> Dict[str, Any]:
        """
        Extract VIN from image using CarAPI OCR
        
        Args:
            image_url: URL of the vehicle image
            
        Returns:
            Extracted VIN and confidence
        """
        cache_key = self._get_cache_key("ocr", image_url)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = self._make_request("vin-ocr", {"image_url": image_url})
        
        if "error" not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # ─── STOLEN VEHICLE CHECK ───────────────────────────────────
    
    def check_stolen_vehicle(self, vin: str) -> Dict[str, Any]:
        """
        Check if vehicle has been reported stolen
        
        Args:
            vin: 17-character VIN number
            
        Returns:
            Stolen vehicle status
        """
        vin = vin.upper().strip()
        cache_key = self._get_cache_key("stolen", vin)
        
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = self._make_request("stolen-vehicle-check", {"vin": vin})
        
        if "error" not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # ─── RECALLS ──────────────────────────────────────────────────
    
    def get_recalls(self, make: str, model: str, year: int) -> Dict[str, Any]:
        """
        Get vehicle recall records
        
        Args:
            make: Vehicle make
            model: Vehicle model
            year: Model year
            
        Returns:
            Recall records and details
        """
        cache_key = self._get_cache_key("recalls", make, model, year)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = self._make_request("recalls", {
            "make": make,
            "model": model,
            "year": year
        })
        
        if "error" not in result:
            self._set_cache(cache_key, result)
        
        return result
    
    # ─── UTILITY ──────────────────────────────────────────────────
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        logger.info("CarAPI cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "cache_size": len(self.cache),
            "cache_ttl": self.cache_ttl,
            "api_key_configured": bool(self.api_key)
        }

# ─── SINGLETON INSTANCE ──────────────────────────────────────

_carapi_service = None

def get_carapi_service() -> CarAPIService:
    """Get CarAPI service instance (singleton)"""
    global _carapi_service
    if _carapi_service is None:
        _carapi_service = CarAPIService()
    return _carapi_service

# ─── CONVENIENCE FUNCTIONS ───────────────────────────────────

def decode_vin(vin: str) -> Dict[str, Any]:
    """Convenience function for VIN decoding"""
    return get_carapi_service().decode_vin(vin)

def get_vehicle_valuation(vin: str) -> Dict[str, Any]:
    """Convenience function for vehicle valuation"""
    return get_carapi_service().get_valuation(vin)

# ─── QUICK TEST ──────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing CarAPI Service...")
    
    service = get_carapi_service()
    
    # Test VIN decode
    test_vin = "1HGBH41JXMN109186"
    result = service.decode_vin(test_vin)
    
    if "error" not in result:
        print(f"✅ VIN Decode: {result.get('make')} {result.get('model')} ({result.get('year')})")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    print("✅ CarAPI Service test complete")
