# app/core/cache.py
import redis
import json
import asyncio
from typing import Optional, Any, Dict
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class Cache:
    """Redis cache manager"""
    
    def __init__(self):
        self.client = None
        self.enabled = settings.REDIS_ENABLED
        
        if self.enabled:
            try:
                self.client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    max_connections=settings.REDIS_MAX_CONNECTIONS
                )
                # Test connection
                self.client.ping()
                logger.info("Redis cache connection established")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.enabled = False
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.enabled:
            return None
        
        try:
            value = self.client.get(key)
            return value
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.enabled:
            return False
        
        try:
            if ttl:
                self.client.setex(key, ttl, value)
            else:
                self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.enabled:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled:
            return False
        
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching pattern"""
        if not self.enabled:
            return False
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment value in cache"""
        if not self.enabled:
            return None
        
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return None
    
    async def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON value from cache"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except:
                return None
        return None
    
    async def set_json(self, key: str, value: Dict, ttl: Optional[int] = None) -> bool:
        """Set JSON value in cache"""
        try:
            return await self.set(key, json.dumps(value), ttl)
        except Exception as e:
            logger.error(f"Cache set JSON error: {e}")
            return False
