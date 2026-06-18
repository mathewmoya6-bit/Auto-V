# api/auth_middleware.py – Flask Auth Middleware (PRODUCTION READY)

import functools
import logging
from flask import request, jsonify, g
from services.supabase_client import get_supabase
from datetime import datetime

logger = logging.getLogger(__name__)

def require_auth(f):
    """
    Decorator that validates the Bearer token and injects the authenticated user.
    Also caches user in Flask's `g` context for the request.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            logger.warning(f"Missing Authorization header from {request.remote_addr}")
            return jsonify({
                'error': 'Missing Authorization header',
                'code': 'AUTH_HEADER_MISSING'
            }), 401

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            logger.warning(f"Invalid token format from {request.remote_addr}")
            return jsonify({
                'error': 'Invalid token format. Use Bearer <token>',
                'code': 'AUTH_FORMAT_INVALID'
            }), 401

        token = parts[1]

        # Check if token is in request cache (g)
        if hasattr(g, 'user') and g.get('user'):
            return f(g.user, *args, **kwargs)

        try:
            supabase = get_supabase()
            user_response = supabase.auth.get_user(token)

            if not user_response or not user_response.user:
                logger.warning(f"Invalid or expired token from {request.remote_addr}")
                return jsonify({
                    'error': 'Invalid or expired token',
                    'code': 'AUTH_TOKEN_INVALID'
                }), 401

            # Cache user in request context
            g.user = user_response.user
            
            # Log successful auth (but not too noisy)
            logger.debug(f"Auth success: {user_response.user.email}")

            return f(user_response.user, *args, **kwargs)

        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            return jsonify({
                'error': 'Authentication failed',
                'code': 'AUTH_FAILED'
            }), 401

    return decorated

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
            try:
                supabase = get_supabase()
                profile_response = supabase.table('user_profiles')\
                    .select('role')\
                    .eq('id', user.id)\
                    .execute()
                
                if not profile_response.data:
                    logger.warning(f"User {user.email} has no profile")
                    return jsonify({
                        'error': 'User profile not found',
                        'code': 'PROFILE_NOT_FOUND'
                    }), 404
                
                role = profile_response.data[0].get('role', 'user')
                
                if role != required_role:
                    logger.warning(f"User {user.email} attempted {required_role} access but has {role} role")
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'code': 'INSUFFICIENT_PERMISSIONS',
                        'required_role': required_role,
                        'user_role': role
                    }), 403
                
                return f(user, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Role check error: {e}")
                return jsonify({
                    'error': 'Failed to verify role',
                    'code': 'ROLE_CHECK_FAILED'
                }), 500
        return decorated
    return decorator
