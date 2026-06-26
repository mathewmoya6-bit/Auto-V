"""
Utility Decorators for FastAPI
Rate limiting, authentication, logging, error handling, retry logic, and performance monitoring
"""

import time
import logging
import os
from functools import wraps
from typing import Optional, Callable, Any, Dict, List, Union
from datetime import datetime
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
import redis
import jwt

logger = logging.getLogger(__name__)

# ─── REDIS CONNECTION ──────────────────────────────────────────

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
REDIS_ENABLED = os.getenv('REDIS_ENABLED', 'true').lower() == 'true'

redis_client = None
redis_available = False

if REDIS_ENABLED:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        redis_available = True
        logger.info("✅ Redis connected for rate limiting")
    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}. Rate limiting disabled.")
        redis_available = False
else:
    logger.info("ℹ️ Redis disabled by configuration")


# ─── RATE LIMITING ─────────────────────────────────────────────

class RateLimiter:
    """Rate limiter class for FastAPI"""
    
    def __init__(self, limit: int = 10, per: int = 60, key_prefix: str = "rate_limit"):
        self.limit = limit
        self.per = per
        self.key_prefix = key_prefix
    
    def get_client_key(self, request: Request) -> str:
        """Get unique client identifier"""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            client_ip = forwarded.split(',')[0].strip()
        
        # Include user ID if available
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"{self.key_prefix}:{user_id}:{request.url.path}"
        
        return f"{self.key_prefix}:{client_ip}:{request.url.path}"
    
    async def check_rate_limit(self, request: Request) -> bool:
        """Check if request is within rate limit"""
        if not redis_available:
            return True
        
        key = self.get_client_key(request)
        
        # Get current count
        current = redis_client.get(key)
        
        if current and int(current) >= self.limit:
            return False
        
        # Increment count
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.per)
        pipe.execute()
        
        return True


def rate_limit(limit: int = 10, per: int = 60):
    """
    Rate limit decorator for FastAPI routes.
    
    Args:
        limit: Number of requests allowed
        per: Time period in seconds
    
    Usage:
        @app.get("/api/endpoint")
        @rate_limit(limit=20, per=60)
        async def my_endpoint():
            return {"success": True}
    """
    limiter = RateLimiter(limit=limit, per=per)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object in args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                logger.warning("No Request object found for rate limiting")
                return await func(*args, **kwargs)
            
            # Check rate limit
            allowed = await limiter.check_rate_limit(request)
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "success": False,
                        "error": f"Rate limit exceeded. Maximum {limit} requests per {per} seconds.",
                        "code": "RATE_LIMIT_EXCEEDED",
                        "retry_after": per
                    }
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ─── AUTHENTICATION ─────────────────────────────────────────────

def require_auth(func: Callable) -> Callable:
    """
    Require authentication decorator for FastAPI routes.
    Uses JWT token from Authorization header.
    
    Usage:
        @app.get("/api/protected")
        @require_auth
        async def protected_endpoint(request: Request):
            user_id = request.state.user_id
            return {"user_id": user_id}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find request object
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if not request:
            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                    break
        
        if not request:
            logger.warning("No Request object found for authentication")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"success": False, "error": "Authentication required", "code": "AUTH_REQUIRED"}
            )
        
        # Get token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"success": False, "error": "Authentication required", "code": "AUTH_REQUIRED"}
            )
        
        token = auth_header.replace('Bearer ', '')
        
        # Verify token
        JWT_SECRET = os.getenv('JWT_SECRET', '')
        JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.state.user_id = payload.get('sub')
            request.state.user_email = payload.get('email')
            request.state.user_role = payload.get('role', 'user')
            request.state.user_payload = payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"success": False, "error": "Token expired", "code": "TOKEN_EXPIRED"}
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"success": False, "error": f"Invalid token: {str(e)}", "code": "INVALID_TOKEN"}
            )
        
        return await func(*args, **kwargs)
    return wrapper


def require_role(required_role: str):
    """
    Require specific role for a route.
    
    Args:
        required_role: Role required to access the route
    
    Usage:
        @app.get("/api/admin")
        @require_role("admin")
        async def admin_endpoint():
            return {"message": "Admin only"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"success": False, "error": "Access denied", "code": "ACCESS_DENIED"}
                )
            
            user_role = getattr(request.state, 'user_role', None)
            if user_role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "error": f"Role '{required_role}' required",
                        "code": "INSUFFICIENT_ROLE"
                    }
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ─── REQUEST LOGGING ───────────────────────────────────────────

def log_request(func: Callable) -> Callable:
    """
    Log request details decorator for FastAPI routes.
    
    Usage:
        @app.get("/api/endpoint")
        @log_request
        async def my_endpoint(request: Request):
            return {"success": True}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        
        # Find request object
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if not request:
            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                    break
        
        if request:
            client_ip = request.client.host if request.client else "unknown"
            forwarded = request.headers.get('X-Forwarded-For')
            if forwarded:
                client_ip = forwarded.split(',')[0].strip()
            
            logger.info(f"📥 {request.method} {request.url.path} from {client_ip}")
        
        try:
            response = await func(*args, **kwargs)
            duration = time.time() - start
            
            if request:
                status_code = 200
                if isinstance(response, dict) and 'status_code' in response:
                    status_code = response['status_code']
                elif isinstance(response, JSONResponse):
                    status_code = response.status_code
                
                logger.info(f"📤 {request.method} {request.url.path} → {status_code} ({duration:.3f}s)")
            
            return response
        except Exception as e:
            duration = time.time() - start
            logger.error(f"❌ {request.method if request else 'Unknown'} {request.url.path if request else 'Unknown'} → ERROR ({duration:.3f}s): {str(e)}")
            raise
    
    return wrapper


# ─── ERROR HANDLING ─────────────────────────────────────────────

def handle_errors(func: Callable) -> Callable:
    """
    Global error handler decorator for FastAPI routes.
    
    Usage:
        @app.get("/api/endpoint")
        @handle_errors
        async def my_endpoint():
            raise ValueError("Something went wrong")
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except ValueError as e:
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "error": str(e), "code": "VALIDATION_ERROR"}
            )
        except Exception as e:
            logger.error(f"Unhandled error in {func.__name__}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"success": False, "error": "An internal error occurred", "code": "INTERNAL_ERROR"}
            )
    return wrapper


# ─── RETRY ON FAILURE ──────────────────────────────────────────

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry decorator for external API calls.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay in seconds
        backoff: Multiplier for exponential backoff
    
    Usage:
        @retry_on_failure(max_retries=3)
        async def call_external_api():
            return await http_client.get('https://api.example.com')
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Max retries reached for {func.__name__}: {str(e)}")
                        raise
                    
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__}: {str(e)}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            return None
        return wrapper
    return decorator


# ─── PERFORMANCE MONITORING ────────────────────────────────────

def measure_performance(func: Callable) -> Callable:
    """
    Measure and log function performance.
    
    Usage:
        @measure_performance
        async def my_function():
            # expensive operation
            return result
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        
        if duration > 1.0:
            logger.warning(f"⚠️ Slow operation: {func.__name__} took {duration:.3f}s")
        else:
            logger.debug(f"⚡ {func.__name__} completed in {duration:.3f}s")
        
        return result
    return wrapper


# ─── CACHE ──────────────────────────────────────────────────────

def cache_response(ttl: int = 300, key_prefix: str = "cache"):
    """
    Cache response decorator using Redis.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    
    Usage:
        @app.get("/api/expensive")
        @cache_response(ttl=3600)
        async def expensive_endpoint():
            return {"data": expensive_calculation()}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not redis_available:
                return await func(*args, **kwargs)
            
            # Build cache key from function name and arguments
            import json
            import hashlib
            
            # Find request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                return await func(*args, **kwargs)
            
            # Build key from path and query params
            path = request.url.path
            query = str(request.query_params)
            key_data = f"{key_prefix}:{func.__name__}:{path}:{query}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                import json
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            import json
            redis_client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator


# ─── COMBINED DECORATORS ──────────────────────────────────────

def public_endpoint(func: Callable) -> Callable:
    """Combine decorators for public endpoints"""
    @wraps(func)
    @handle_errors
    @log_request
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def protected_endpoint(func: Callable) -> Callable:
    """Combine decorators for protected endpoints"""
    @wraps(func)
    @handle_errors
    @log_request
    @require_auth
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def admin_endpoint(func: Callable) -> Callable:
    """Combine decorators for admin endpoints"""
    @wraps(func)
    @handle_errors
    @log_request
    @require_auth
    @require_role("admin")
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


# ─── FASTAPI DEPENDENCIES ──────────────────────────────────────

async def get_rate_limit_status() -> Dict[str, Any]:
    """Get rate limit status for current request"""
    return {
        "redis_available": redis_available,
        "rate_limiting_enabled": REDIS_ENABLED
    }


# ─── EXPORTS ──────────────────────────────────────────────────

__all__ = [
    # Rate Limiting
    "rate_limit",
    "RateLimiter",
    
    # Authentication
    "require_auth",
    "require_role",
    
    # Logging
    "log_request",
    
    # Error Handling
    "handle_errors",
    
    # Retry
    "retry_on_failure",
    
    # Performance
    "measure_performance",
    
    # Cache
    "cache_response",
    
    # Combined Decorators
    "public_endpoint",
    "protected_endpoint",
    "admin_endpoint",
    
    # Dependencies
    "get_rate_limit_status",
]
