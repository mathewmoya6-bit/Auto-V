# app/middleware/rate_limit.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Dict, Tuple
import time
import redis
from collections import defaultdict
import threading

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(self, app):
        super().__init__(app)
        self.redis_client = None
        self.enabled = settings.RATELIMIT_ENABLED
        
        if self.enabled:
            try:
                self.redis_client = redis.from_url(
                    settings.RATELIMIT_STORAGE_URI,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Rate limiting Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis for rate limiting: {e}")
                self.enabled = False
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        if not self.enabled:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get rate limit key
        path = request.url.path
        rate_limit_key = f"ratelimit:{client_ip}:{path}"
        
        try:
            # Get current count
            current = self.redis_client.get(rate_limit_key)
            
            if current is None:
                # First request from this IP
                self.redis_client.setex(
                    rate_limit_key,
                    60,  # 1 minute window
                    1
                )
            else:
                count = int(current)
                
                # Check if exceeded
                max_requests = settings.IP_RATE_LIMIT
                
                if count >= max_requests:
                    logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Too many requests. Please try again later.",
                            "retry_after": 60
                        },
                        headers={"Retry-After": "60"}
                    )
                
                # Increment count
                self.redis_client.incr(rate_limit_key)
        
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting if Redis fails
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        try:
            remaining = int(self.redis_client.get(rate_limit_key) or 0)
            response.headers["X-RateLimit-Limit"] = str(settings.IP_RATE_LIMIT)
            response.headers["X-RateLimit-Remaining"] = str(max(0, settings.IP_RATE_LIMIT - remaining))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        except:
            pass
        
        return response
