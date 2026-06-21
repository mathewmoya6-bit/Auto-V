# utils/decorators.py
import time
import logging
from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from datetime import datetime
import redis
import os

logger = logging.getLogger(__name__)

# ─── REDIS CONNECTION ──────────────────────────────────────

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    redis_available = True
    logger.info("✅ Redis connected for rate limiting")
except:
    redis_available = False
    logger.warning("⚠️ Redis not available. Rate limiting disabled.")

# ─── RATE LIMITING ─────────────────────────────────────────

def rate_limit(limit=10, per=60):
    """
    Rate limit decorator
    
    Args:
        limit: Number of requests allowed
        per: Time period in seconds
    
    Usage:
        @rate_limit(limit=20, per=60)
        def my_endpoint():
            return {"success": True}
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not redis_available:
                return f(*args, **kwargs)
            
            # Get client IP
            client_ip = request.remote_addr
            forwarded = request.headers.get('X-Forwarded-For')
            if forwarded:
                client_ip = forwarded.split(',')[0]
            
            # Rate limit key
            key = f"rate_limit:{client_ip}:{request.path}"
            
            # Check current count
            current = redis_client.get(key)
            
            if current and int(current) >= limit:
                return jsonify({
                    'success': False,
                    'error': f'Rate limit exceeded. Maximum {limit} requests per {per} seconds.',
                    'retry_after': per,
                    'code': 'RATE_LIMIT_EXCEEDED'
                }), 429
            
            # Increment count
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, per)
            pipe.execute()
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ─── AUTHENTICATION ────────────────────────────────────────

def require_auth(f):
    """
    Require authentication decorator
    
    Usage:
        @require_auth
        def my_endpoint():
            return {"success": True}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            request.user_id = get_jwt_identity()
            return f(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Authentication failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
    return decorated_function

# ─── REQUEST LOGGING ──────────────────────────────────────

def log_request(f):
    """
    Log request details decorator
    
    Usage:
        @log_request
        def my_endpoint():
            return {"success": True}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start = time.time()
        
        # Log request
        logger.info(f"📥 {request.method} {request.path} from {request.remote_addr}")
        
        response = f(*args, **kwargs)
        
        # Log response time
        duration = time.time() - start
        status_code = response[1] if isinstance(response, tuple) else 200
        logger.info(f"📤 {request.method} {request.path} → {status_code} ({duration:.3f}s)")
        
        return response
    return decorated_function

# ─── ERROR HANDLING ────────────────────────────────────────

def handle_errors(f):
    """
    Global error handler decorator
    
    Usage:
        @handle_errors
        def my_endpoint():
            raise ValueError("Something went wrong")
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'code': 'VALIDATION_ERROR'
            }), 400
        except Exception as e:
            logger.error(f"Unhandled error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': 'An internal error occurred',
                'code': 'INTERNAL_ERROR'
            }), 500
    return decorated_function

# ─── RETRY ON FAILURE ──────────────────────────────────────

def retry_on_failure(max_retries=3, delay=1, backoff=2):
    """
    Retry decorator for external API calls
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay in seconds
        backoff: Multiplier for exponential backoff
    
    Usage:
        @retry_on_failure(max_retries=3)
        def call_external_api():
            return requests.get('https://api.example.com')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Max retries reached for {f.__name__}: {str(e)}")
                        raise
                    
                    logger.warning(f"Retry {retries}/{max_retries} for {f.__name__}: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return None
        return decorated_function
    return decorator

# ─── PERFORMANCE MONITORING ──────────────────────────────

def measure_performance(f):
    """
    Measure and log function performance
    
    Usage:
        @measure_performance
        def my_function():
            # expensive operation
            return result
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start
        
        if duration > 1.0:
            logger.warning(f"Slow operation: {f.__name__} took {duration:.3f}s")
        else:
            logger.debug(f"{f.__name__} completed in {duration:.3f}s")
        
        return result
    return decorated_function
