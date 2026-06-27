# app/services/vehicle_service.py
import requests
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.core.cache import Cache

logger = logging.getLogger(__name__)

class VehicleService:
    """Vehicle data service with VIN decoding and market data"""
    
    def __init__(self):
        self.carapi_key = settings.CARAPI_KEY
        self.cache = Cache()
        self.ai_engine = None
        
        # Initialize AI engine if enabled
        if settings.AI_PREDICTIONS_ENABLED:
            try:
                from app.services.ai_engine import AIEngine
                self.ai_engine = AIEngine()
            except Exception as e:
                logger.warning(f"AI engine initialization failed: {e}")
    
    async def decode_vin(self, vin: str) -> Optional[Dict[str, Any]]:
        """Decode VIN using external API"""
        try:
            # Check cache first
            cache_key = f"vin:{vin}"
            cached = await self.cache.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Call CarAPI
            response = requests.get(
                f"https://api.carapi.com/vin/decode",
                params={
                    "vin": vin,
                    "api_key": self.carapi_key
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant fields
                result = {
                    'make': data.get('make'),
                    'model': data.get('model'),
                    'year': data.get('year'),
                    'engine_type': data.get('engine_type'),
                    'transmission': data.get('transmission'),
                    'fuel_type': data.get('fuel_type'),
                    'vehicle_type': data.get('vehicle_type'),
                    'manufacturer': data.get('manufacturer'),
                    'plant_city': data.get('plant_city'),
                    'plant_country': data.get('plant_country')
                }
                
                # Cache for 7 days
                await self.cache.set(cache_key, json.dumps(result), 604800)
                
                return result
            else:
                logger.warning(f"CarAPI error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"VIN decode error: {str(e)}")
            return None
    
    async def get_market_value(self, make: str, model: str, year: int) -> Optional[Dict[str, Any]]:
        """Get market value for a vehicle"""
        try:
            cache_key = f"market:{make}:{model}:{year}"
            cached = await self.cache.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Call market value API
            # This is a placeholder - replace with actual API
            response = requests.get(
                f"https://api.carapi.com/valuation",
                params={
                    "make": make,
                    "model": model,
                    "year": year,
                    "api_key": self.carapi_key
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Cache for 24 hours
                await self.cache.set(cache_key, json.dumps(data), 86400)
                
                return data
            else:
                logger.warning(f"Market value API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Market value error: {str(e)}")
            return None
    
    async def get_similar_vehicles(self, make: str, model: str, year: int, limit: int = 10) -> list:
        """Get similar vehicles for comparison"""
        try:
            # Query database for similar vehicles
            # This would normally query your database
            # Placeholder implementation
            return []
            
        except Exception as e:
            logger.error(f"Similar vehicles error: {str(e)}")
            return []
    
    async def predict_price(self, vehicle_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Predict vehicle price using AI"""
        try:
            if not self.ai_engine:
                return None
            
            # Check cache
            cache_key = f"price_prediction:{json.dumps(vehicle_data, sort_keys=True)}"
            cached = await self.cache.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Get AI prediction
            prediction = await self.ai_engine.predict_price(vehicle_data)
            
            if prediction:
                # Cache for 24 hours
                await self.cache.set(cache_key, json.dumps(prediction), 86400)
            
            return prediction
            
        except Exception as e:
            logger.error(f"Price prediction error: {str(e)}")
            return None
