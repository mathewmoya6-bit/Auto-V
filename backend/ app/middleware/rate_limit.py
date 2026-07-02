# app/middleware/rate_limit.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Dict, Tuple, Optional
import time
import redis
from collections import defaultdict
import threading
import hashlib
import json

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis with support for:
    - IP-based rate limiting
    - Path-based rate limiting
    - User-based rate limiting (for authenticated requests)
    - Distributed rate limiting using Redis
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.redis_client = None
        self.enabled = settings.RATELIMIT_ENABLED
        self.redis_available = False
        
        if self.enabled:
            try:
                redis_url = getattr(settings, 'RATELIMIT_STORAGE_URI', None)
                if not redis_url:
                    # Fallback to REDIS_URL if RATELIMIT_STORAGE_URI not set
                    redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
                
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                self.redis_client.ping()
                self.redis_available = True
                logger.info("✅ Rate limiting Redis connection established")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Redis for rate limiting: {e}")
                self.redis_available = False
                self.enabled = False
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        if not self.enabled or not self.redis_available:
            return await call_next(request)
        
        # Get client IP - handle proxy headers
        client_ip = self._get_client_ip(request)
        
        # Get rate limit key based on authentication status
        rate_limit_key = self._get_rate_limit_key(request, client_ip)
        
        # Get rate limit configuration
        limit_config = self._get_limit_config(request)
        max_requests = limit_config.get('requests', settings.IP_RATE_LIMIT)
        window_seconds = limit_config.get('window', 60)
        
        try:
            # Get current count
            current = self.redis_client.get(rate_limit_key)
            
            if current is None:
                # First request from this IP
                self.redis_client.setex(
                    rate_limit_key,
                    window_seconds,
                    1
                )
            else:
                count = int(current)
                
                # Check if exceeded
                if count >= max_requests:
                    ttl = self.redis_client.ttl(rate_limit_key)
                    if ttl < 0:
                        ttl = window_seconds
                    
                    logger.warning(
                        f"Rate limit exceeded",
                        extra={
                            "client_ip": client_ip,
                            "path": request.url.path,
                            "count": count,
                            "max": max_requests,
                            "ttl": ttl
                        }
                    )
                    
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Too many requests. Please try again later.",
                            "retry_after": ttl,
                            "status_code": 429,
                            "path": request.url.path
                        },
                        headers={
                            "Retry-After": str(ttl),
                            "X-RateLimit-Limit": str(max_requests),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int(time.time()) + ttl)
                        }
                    )
                
                # Increment count
                self.redis_client.incr(rate_limit_key)
                current_count = count + 1
        
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting if Redis fails
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        try:
            remaining = int(self.redis_client.get(rate_limit_key) or 0)
            ttl = self.redis_client.ttl(rate_limit_key)
            if ttl < 0:
                ttl = window_seconds
            
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - remaining))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + ttl)
        except:
            pass
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address considering proxy headers"""
        # Check for forwarded headers (nginx, Cloudflare, etc.)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the list
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _get_rate_limit_key(self, request: Request, client_ip: str) -> str:
        """Generate rate limit key based on authentication status"""
        # Check if user is authenticated
        user_id = None
        if hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
        elif hasattr(request, 'user'):
            user_id = getattr(request.user, 'id', None)
        
        path = request.url.path
        
        # Use user_id for authenticated users for better tracking
        if user_id:
            return f"ratelimit:user:{user_id}:{path}"
        
        # Use IP for unauthenticated users
        return f"ratelimit:ip:{client_ip}:{path}"
    
    def _get_limit_config(self, request: Request) -> Dict:
        """Get rate limit configuration based on endpoint"""
        path = request.url.path
        method = request.method
        
        # Default configuration
        config = {
            'requests': settings.IP_RATE_LIMIT,
            'window': 60
        }
        
        # Stricter limits for authentication endpoints
        if '/auth/login' in path or '/auth/register' in path:
            config['requests'] = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
            config['window'] = 300  # 5 minutes
            
        elif '/auth/reset-password' in path:
            config['requests'] = 3
            config['window'] = 3600  # 1 hour
            
        elif '/payments' in path and method == 'POST':
            config['requests'] = 5
            config['window'] = 300  # 5 minutes
            
        elif '/api/webhooks' in path:
            # Webhooks can have higher limits
            config['requests'] = 500
            config['window'] = 60
            
        elif '/admin' in path:
            config['requests'] = getattr(settings, 'ADMIN_RATE_LIMIT', 200)
            config['window'] = 60
            
        elif '/valuations' in path and method == 'POST':
            config['requests'] = 20
            config['window'] = 300  # 5 minutes
            
        return config


class RateLimitPerEndpoint:
    """
    Decorator for per-endpoint rate limiting.
    Usage:
        @RateLimitPerEndpoint(requests=10, window=60)
        async def my_endpoint():
            ...
    """
    
    def __init__(self, requests: int = 100, window: int = 60, key_prefix: str = ""):
        self.requests = requests
        self.window = window
        self.key_prefix = key_prefix
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            # Get request object from args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for arg in kwargs.values():
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                # No request found, execute without rate limiting
                return await func(*args, **kwargs)
            
            # Get client IP
            client_ip = request.client.host if request.client else "unknown"
            
            # Create rate limit key
            key = f"ratelimit:endpoint:{self.key_prefix}:{client_ip}:{request.url.path}"
            
            # Redis connection
            redis_client = None
            try:
                redis_url = getattr(settings, 'RATELIMIT_STORAGE_URI', None) or getattr(settings, 'REDIS_URL', None)
                if redis_url:
                    redis_client = redis.from_url(redis_url, decode_responses=True)
                    redis_client.ping()
            except:
                # Redis not available, skip rate limiting
                return await func(*args, **kwargs)
            
            try:
                current = redis_client.get(key)
                
                if current is None:
                    redis_client.setex(key, self.window, 1)
                else:
                    count = int(current)
                    if count >= self.requests:
                        ttl = redis_client.ttl(key)
                        if ttl < 0:
                            ttl = self.window
                        return JSONResponse(
                            status_code=429,
                            content={
                                "detail": f"Rate limit exceeded for this endpoint. Try again in {ttl} seconds.",
                                "retry_after": ttl,
                                "status_code": 429
                            },
                            headers={"Retry-After": str(ttl)}
                        )
                    redis_client.incr(key)
            except Exception as e:
                logger.error(f"Per-endpoint rate limit error: {e}")
            
            return await func(*args, **kwargs)
        
        return wrapper


# Simplified decorator for route handlers
def rate_limit(requests: int = 100, window: int = 60, key: str = ""):
    """
    Rate limit decorator for FastAPI routes.
    
    Usage:
        @app.get("/api/endpoint")
        @rate_limit(requests=10, window=60, key="custom_endpoint")
        async def endpoint():
            ...
    """
    return RateLimitPerEndpoint(requests=requests, window=window, key_prefix=key)


class InMemoryRateLimiter:
    """
    Fallback in-memory rate limiter when Redis is unavailable.
    Not recommended for production with multiple instances.
    """
    
    def __init__(self):
        self.requests = defaultdict(int)
        self.lock = threading.Lock()
        self.last_reset = time.time()
    
    def check(self, key: str, limit: int = 100, window: int = 60) -> Tuple[bool, int]:
        """Check if rate limit is exceeded. Returns (allowed, remaining)"""
        now = time.time()
        
        # Reset if window has passed
        if now - self.last_reset > window:
            with self.lock:
                if now - self.last_reset > window:
                    self.requests.clear()
                    self.last_reset = now
        
        with self.lock:
            count = self.requests[key]
            if count >= limit:
                return False, 0
            
            self.requests[key] = count + 1
            return True, limit - count - 1
    
    def reset(self):
        """Reset all counters"""
        with self.lock:
            self.requests.clear()
            self.last_reset = time.time()
