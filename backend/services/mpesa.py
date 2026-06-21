# services/mpesa.py - Add rate limiting for status endpoint

from functools import wraps
from flask import request, jsonify
import time

# ─── RATE LIMITING FOR STATUS ENDPOINT ─────────────────────
_status_rate_limiter = {}

def rate_limit_status(max_requests=10, per_seconds=60):
    """Rate limit decorator for status endpoint."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get client IP
            client_ip = request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown')
            
            # Get current time
            now = time.time()
            
            # Initialize if not exists
            if client_ip not in _status_rate_limiter:
                _status_rate_limiter[client_ip] = {'requests': [], 'blocked_until': 0}
            
            # Check if blocked
            if _status_rate_limiter[client_ip]['blocked_until'] > now:
                retry_after = int(_status_rate_limiter[client_ip]['blocked_until'] - now) + 1
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': retry_after
                }), 429, {'Retry-After': str(retry_after)}
            
            # Get request history
            request_history = _status_rate_limiter[client_ip]['requests']
            
            # Clean old requests
            request_history = [t for t in request_history if t > now - per_seconds]
            _status_rate_limiter[client_ip]['requests'] = request_history
            
            # Check limit
            if len(request_history) >= max_requests:
                _status_rate_limiter[client_ip]['blocked_until'] = now + per_seconds
                return jsonify({
                    'error': 'Too many requests. Please wait.',
                    'retry_after': per_seconds
                }), 429, {'Retry-After': str(per_seconds)}
            
            # Add current request
            request_history.append(now)
            _status_rate_limiter[client_ip]['requests'] = request_history
            
            return f(*args, **kwargs)
        return wrapped
    return decorator
