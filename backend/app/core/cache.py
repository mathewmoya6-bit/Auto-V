# app/core/cache.py (UPDATED FOR REDIS 5.2.0)
import redis
import json
import asyncio
from typing import Optional, Dict, Any, Union, List
import logging
from datetime import datetime, timedelta
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)

class Cache:
    """
    Redis cache manager with async support
    Compatible with Redis 5.2.0+
    """
    
    def __init__(self):
        self.client = None
        self.enabled = settings.REDIS_ENABLED
        self._initialized = False
        self._connection_pool = None
        
        if self.enabled:
            try:
                # Create connection pool for better performance
                self._connection_pool = redis.ConnectionPool.from_url(
                    settings.REDIS_URL,
                    max_connections=settings.REDIS_MAX_CONNECTIONS,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                self.client = redis.Redis(
                    connection_pool=self._connection_pool,
                    decode_responses=True
                )
                
                # Test connection
                self.client.ping()
                self._initialized = True
                logger.info(f"Redis cache connection established (v{redis.__version__})")
                
                # Get Redis info
                info = self.client.info()
                logger.info(f"Redis version: {info.get('redis_version')}")
                logger.info(f"Redis memory: {info.get('used_memory_human')}")
                
            except redis.ConnectionError as e:
                logger.error(f"Redis connection failed: {e}")
                self.enabled = False
                self.client = None
            except Exception as e:
                logger.error(f"Redis initialization error: {e}")
                self.enabled = False
                self.client = None
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Value if found, None otherwise
        """
        if not self.enabled or not self._initialized:
            return None
        try:
            # Use synchronous client in async context
            return await asyncio.to_thread(self.client.get, key)
        except redis.RedisError as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected cache get error: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with optional TTL
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self._initialized:
            return False
        try:
            if ttl:
                return await asyncio.to_thread(
                    self.client.setex, key, ttl, value
                )
            else:
                return await asyncio.to_thread(
                    self.client.set, key, value
                )
        except redis.RedisError as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self._initialized:
            return False
        try:
            result = await asyncio.to_thread(self.client.delete, key)
            return result > 0
        except redis.RedisError as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.enabled or not self._initialized:
            return False
        try:
            result = await asyncio.to_thread(self.client.exists, key)
            return result > 0
        except redis.RedisError as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected cache exists error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment value in cache
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value if successful, None otherwise
        """
        if not self.enabled or not self._initialized:
            return None
        try:
            return await asyncio.to_thread(self.client.incr, key, amount)
        except redis.RedisError as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected cache increment error: {e}")
            return None
    
    async def get_json(self, key: str) -> Optional[Dict]:
        """
        Get JSON value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Parsed JSON if found, None otherwise
        """
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error for key {key}: {e}")
                return None
        return None
    
    async def set_json(
        self, 
        key: str, 
        value: Dict, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set JSON value in cache
        
        Args:
            key: Cache key
            value: Dictionary to store as JSON
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, ttl)
        except json.JSONEncodeError as e:
            logger.error(f"JSON encode error for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected set JSON error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern
        
        Args:
            pattern: Pattern to match (e.g., "user:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self._initialized:
            return 0
        try:
            keys = await asyncio.to_thread(self.client.keys, pattern)
            if keys:
                return await asyncio.to_thread(self.client.delete, *keys)
            return 0
        except redis.RedisError as e:
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected clear pattern error: {e}")
            return 0
    
    async def set_with_ttl(
        self, 
        key: str, 
        value: str, 
        ttl: int
    ) -> bool:
        """Set value with TTL (alias for set with ttl)"""
        return await self.set(key, value, ttl)
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds, None if key doesn't exist or error
        """
        if not self.enabled or not self._initialized:
            return None
        try:
            return await asyncio.to_thread(self.client.ttl, key)
        except redis.RedisError as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected TTL error: {e}")
            return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on an existing key
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self._initialized:
            return False
        try:
            return await asyncio.to_thread(self.client.expire, key, ttl)
        except redis.RedisError as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected expire error: {e}")
            return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """
        Get multiple values from cache
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary of key-value pairs
        """
        if not self.enabled or not self._initialized:
            return {key: None for key in keys}
        try:
            values = await asyncio.to_thread(self.client.mget, keys)
            return {key: value for key, value in zip(keys, values)}
        except redis.RedisError as e:
            logger.error(f"Cache get_many error: {e}")
            return {key: None for key in keys}
        except Exception as e:
            logger.error(f"Unexpected get_many error: {e}")
            return {key: None for key in keys}
    
    async def set_many(
        self, 
        mapping: Dict[str, str], 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set multiple values in cache
        
        Args:
            mapping: Dictionary of key-value pairs
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self._initialized:
            return False
        try:
            # Use pipeline for better performance
            pipeline = self.client.pipeline()
            if ttl:
                for key, value in mapping.items():
                    pipeline.setex(key, ttl, value)
            else:
                pipeline.mset(mapping)
            pipeline.execute()
            return True
        except redis.RedisError as e:
            logger.error(f"Cache set_many error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected set_many error: {e}")
            return False
    
    async def flush_all(self) -> bool:
        """
        Clear all cache (use with caution!)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self._initialized:
            return False
        try:
            await asyncio.to_thread(self.client.flushall)
            logger.warning("Cache flushed all keys")
            return True
        except redis.RedisError as e:
            logger.error(f"Cache flush_all error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected flush_all error: {e}")
            return False
    
    def get_client(self) -> redis.Redis:
        """
        Get raw Redis client (for advanced operations)
        
        Returns:
            Redis client instance
        """
        return self.client
    
    def is_healthy(self) -> bool:
        """
        Check if cache is healthy
        
        Returns:
            True if cache is healthy, False otherwise
        """
        if not self.enabled or not self._initialized:
            return False
        try:
            self.client.ping()
            return True
        except:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled or not self._initialized:
            return {"enabled": False}
        
        try:
            info = self.client.info()
            return {
                "enabled": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "total_connections": info.get("total_connections_received"),
                "total_commands": info.get("total_commands_processed"),
                "uptime": info.get("uptime_in_seconds"),
                "connected_clients": info.get("connected_clients")
            }
        except:
            return {"enabled": True, "error": "Unable to get stats"}

# Global cache instance
cache = Cache()
