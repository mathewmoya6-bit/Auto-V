# auth_decorators.py – AUTO-V Authentication & Authorization Decorators (Flask)

import logging
import time
import functools
from threading import Lock
from flask import request, jsonify
from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# ============================================================
# TOKEN CACHE (Thread-safe, TTL 5 minutes)
# ============================================================

_cache = {}
_cache_lock = Lock()
CACHE_TTL = 300  # 5 minutes

def get_cached_user(token: str):
    """Return cached user or None if expired."""
    with _cache_lock:
        entry = _cache.get(token)
        if entry and entry['expires_at'] > time.time():
            return entry['user']
    return None

def set_cached_user(token: str, user):
    with _cache_lock:
        _cache[token] = {
            'user': user,
            'expires_at': time.time() + CACHE_TTL
        }

# ============================================================
# DECORATOR: REQUIRE AUTH
# ============================================================

def require_auth(f):
    """
    Decorator that validates the Bearer token and injects the
    authenticated user into the route function.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            logger.warning("Missing Authorization header")
            return jsonify({'error': 'Missing Authorization header'}), 401

        # Validate format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            logger.warning(f"Invalid token format: {auth_header}")
            return jsonify({'error': 'Invalid token format. Use Bearer <token>'}), 401

        token = parts[1]

        # Check cache first
        user = get_cached_user(token)
        if user:
            logger.debug(f"User {user.get('email')} authenticated from cache")
            return f(user, *args, **kwargs)

        # No cache hit – verify with Supabase
        try:
            supabase = get_supabase()
            user_response = supabase.auth.get_user(token)

            if not user_response or not user_response.user:
                # Could be expired or invalid
                logger.warning(f"Token validation failed: user not found")
                return jsonify({'error': 'Invalid or expired token'}), 401

            # Cache the user object
            user_obj = user_response.user
            set_cached_user(token, user_obj)

            # Optionally, also fetch profile to enrich user object
            # (can be added if needed)
            logger.info(f"User {user_obj.get('email')} authenticated")
            return f(user_obj, *args, **kwargs)

        except Exception as e:
            error_msg = str(e)
            if 'expired' in error_msg.lower():
                logger.warning(f"Token expired for request: {error_msg}")
                return jsonify({'error': 'Token expired'}), 401
            elif 'invalid' in error_msg.lower():
                logger.warning(f"Invalid token: {error_msg}")
                return jsonify({'error': 'Invalid token'}), 401
            else:
                logger.error(f"Authentication error: {error_msg}", exc_info=True)
                return jsonify({'error': 'Authentication failed'}), 401

    return decorated

# ============================================================
# DECORATOR: REQUIRE ROLE (RBAC)
# ============================================================

def require_role(required_role: str):
    """
    Decorator that checks the user's role after authentication.
    Must be used AFTER @require_auth.

    Usage:
        @app.route('/admin')
        @require_auth
        @require_role('admin')
        def admin_only(user):
            return jsonify({'message': 'Welcome, admin!'})
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(user, *args, **kwargs):
            # Get the user's role from the Supabase user object's user_metadata
            # or from the user_profiles table (we might have it in a session)
            # For simplicity, we assume the role is stored in user.user_metadata or we fetch it.
            # If not, we can fetch it from the database.
            role = user.user_metadata.get('role') if user.user_metadata else None

            # If role not in metadata, fetch from user_profiles table
            if not role:
                try:
                    supabase = get_supabase()
                    profile_resp = supabase.table('user_profiles')\
                        .select('role')\
                        .eq('id', user.id)\
                        .execute()
                    if profile_resp.data:
                        role = profile_resp.data[0].get('role', 'user')
                except Exception as e:
                    logger.error(f"Failed to fetch user role: {e}")
                    return jsonify({'error': 'Unable to verify role'}), 500

            if role != required_role:
                logger.warning(f"User {user.email} attempted access to {required_role} role")
                return jsonify({'error': 'Insufficient permissions'}), 403

            return f(user, *args, **kwargs)
        return decorated
    return decorator

# ============================================================
# DECORATOR: OPTIONAL CACHE BUSTING (if needed)
# ============================================================

def clear_auth_cache():
    """Clear the token cache (useful for tests or forced logout)."""
    with _cache_lock:
        _cache.clear()
