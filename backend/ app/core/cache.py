# app/core/cache.py
import redis
import json
import asyncio
from typing import Optional, Dict, Any, Union
import logging
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)

class Cache:
    """Redis cache manager with async support"""
    
    def __init__(self):
        self.client = None
        self.enabled = settings.REDIS_ENABLED
        self._initialized = False
        
        if self.enabled:
            try:
                self.client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    max_connections=settings.REDIS_MAX_CONNECTIONS,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
                self.client.ping()
                self._initialized = True
                logger.info("Redis cache connection established")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self.enabled = False
                self.client = None
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.enabled or not self._initialized:
            return None
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        if not self.enabled or not self._initialized:
            return False
        try:
            if ttl:
                self.client.setex(key, ttl, value)
            else:
                self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.enabled or not self._initialized:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled or not self._initialized:
            return False
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment value in cache"""
        if not self.enabled or not self._initialized:
            return None
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    async def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON value from cache"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def set_json(self, key: str, value: Dict, ttl: Optional[int] = None) -> bool:
        """Set JSON value in cache"""
        try:
            return await self.set(key, json.dumps(value), ttl)
        except Exception as e:
            logger.error(f"Cache set JSON error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching pattern"""
        if not self.enabled or not self._initialized:
            return False
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return False
    
    async def set_with_ttl(self, key: str, value: str, ttl: int) -> bool:
        """Set value with TTL (alias for set with ttl)"""
        return await self.set(key, value, ttl)
