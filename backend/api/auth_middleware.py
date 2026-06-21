# api/auth_middleware.py - FIXED

import os
import logging
import jwt
import hashlib
import ipaddress
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from flask import request, jsonify, g, current_app

# ─── FIXED: Import the correct Supabase client ──────────────────
from services.supabase_client import get_supabase_client as get_supabase

logger = logging.getLogger(__name__)

# ─── CONFIG ────────────────────────────────────────────────
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET', '')
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
AUTH_SESSION_TIMEOUT = int(os.getenv('AUTH_SESSION_TIMEOUT', '3600'))
AUTH_REFRESH_TIMEOUT = int(os.getenv('AUTH_REFRESH_TIMEOUT', '604800'))

# ─── ROLE HIERARCHY ────────────────────────────────────────
ROLES = {
    'admin': 100,
    'manager': 80,
    'inspector': 60,
    'staff': 40,
    'agent': 20,
    'user': 10,
    'guest': 0
}

ROLE_PERMISSIONS = {
    'admin': ['*'],
    'manager': ['view_all', 'edit_all', 'view_reports'],
    'inspector': ['view_inspections', 'create_inspections', 'edit_inspections'],
    'staff': ['view_own', 'edit_own'],
    'agent': ['create_requests', 'view_own'],
    'user': ['view_own'],
    'guest': []
}

# ─── PUBLIC ENDPOINTS ──────────────────────────────────────
PUBLIC_ENDPOINTS = [
    '/api/health',
    '/api/mpesa/callback',
    '/api/mpesa/callback-debug',
    '/api/mpesa/config-status',
    '/api/auth/login',
    '/api/auth/refresh',
    '/api/auth/reset-password',
    '/api/auth/register',
    '/api/ping',
    '/api/test'
]

# ─── IP WHITELIST (OPTIONAL) ──────────────────────────────
IP_WHITELIST = os.getenv('IP_WHITELIST', '').split(',') if os.getenv('IP_WHITELIST') else []
IP_BLACKLIST = os.getenv('IP_BLACKLIST', '').split(',') if os.getenv('IP_BLACKLIST') else []


# ─── SESSION MANAGEMENT ────────────────────────────────────
class SessionManager:
    """Manage user sessions with tracking and revocation."""

    @staticmethod
    def create_session(user_id: str, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new session for a user."""
        try:
            # ─── FIXED: Use the correct Supabase function ──────────
            supabase = get_supabase()
            session_data = {
                'user_id': user_id,
                'device_id': device_info.get('device_id', 'unknown'),
                'device_name': device_info.get('device_name', 'Unknown Device'),
                'ip_address': device_info.get('ip_address', request.remote_addr),
                'user_agent': device_info.get('user_agent', request.user_agent.string if request.user_agent else 'unknown'),
                'session_token': hashlib.sha256(os.urandom(32)).hexdigest(),
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=AUTH_SESSION_TIMEOUT)).isoformat(),
                'is_active': True,
                'last_activity': datetime.now().isoformat()
            }

            result = supabase.table('user_sessions').insert(session_data).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return None

    @staticmethod
    def validate_session(session_token: str) -> Tuple[bool, Optional[Dict]]:
        """Validate a session token."""
        try:
            # ─── FIXED: Use the correct Supabase function ──────────
            supabase = get_supabase()
            result = supabase.table('user_sessions')\
                .select('*')\
                .eq('session_token', session_token)\
                .eq('is_active', True)\
                .execute()

            if not result.data:
                return False, None

            session = result.data[0]
            expires_at = datetime.fromisoformat(session['expires_at'])

            if datetime.now() > expires_at:
                supabase.table('user_sessions').update({
                    'is_active': False,
                    'expired_at': datetime.now().isoformat()
                }).eq('id', session['id']).execute()
                return False, None

            supabase.table('user_sessions').update({
                'last_activity': datetime.now().isoformat()
            }).eq('id', session['id']).execute()

            return True, session
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return False, None

    @staticmethod
    def revoke_session(session_token: str) -> bool:
        """Revoke a session."""
        try:
            # ─── FIXED: Use the correct Supabase function ──────────
            supabase = get_supabase()
            result = supabase.table('user_sessions')\
                .update({
                    'is_active': False,
                    'revoked_at': datetime.now().isoformat()
                })\
                .eq('session_token', session_token)\
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Session revocation error: {e}")
            return False

    @staticmethod
    def revoke_all_sessions(user_id: str) -> bool:
        """Revoke all sessions for a user."""
        try:
            # ─── FIXED: Use the correct Supabase function ──────────
            supabase = get_supabase()
            result = supabase.table('user_sessions')\
                .update({
                    'is_active': False,
                    'revoked_at': datetime.now().isoformat()
                })\
                .eq('user_id', user_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Revoke all sessions error: {e}")
            return False


# ─── AUDIT LOGGING ─────────────────────────────────────────
class AuditLogger:
    """Log all authentication and authorization events."""

    @staticmethod
    def log_event(user_id: Optional[str], action: str, details: Dict[str, Any], status: str = 'success'):
        """Log an audit event."""
        try:
            # ─── FIXED: Use the correct Supabase function ──────────
            supabase = get_supabase()
            audit_data = {
                'user_id': user_id,
                'action': action,
                'path': request.path,
                'method': request.method,
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', 'unknown'),
                'details': details,
                'status': status,
                'created_at': datetime.now().isoformat()
            }
            supabase.table('audit_logs').insert(audit_data).execute()
        except Exception as e:
            logger.error(f"Audit logging error: {e}")


# ─── IP VALIDATION ─────────────────────────────────────────
def validate_ip(ip: str) -> Tuple[bool, str]:
    """Validate IP against whitelist/blacklist."""
    if IP_BLACKLIST:
        for blocked in IP_BLACKLIST:
            if blocked in ip:
                return False, f"IP {ip} is blacklisted"

    if IP_WHITELIST:
        for allowed in IP_WHITELIST:
            if allowed in ip:
                return True, "IP whitelisted"
        return False, f"IP {ip} not in whitelist"

    return True, "IP allowed"


# ─── JWT VALIDATION ────────────────────────────────────────
def validate_jwt(token: str) -> dict:
    """Validate JWT token with strict verification."""
    if not token:
        raise ValueError("No token provided")

    try:
        if SUPABASE_JWT_SECRET:
            try:
                payload = jwt.decode(
                    token,
                    SUPABASE_JWT_SECRET,
                    algorithms=['HS256'],
                    audience='authenticated',
                    options={
                        'verify_aud': True,
                        'verify_exp': True,
                        'verify_iss': True
                    }
                )
                logger.debug(f"JWT validated with secret for: {payload.get('sub')}")
                return payload
            except jwt.ExpiredSignatureError:
                logger.warning("JWT token expired")
                raise ValueError("Token expired")
            except jwt.InvalidAudienceError:
                logger.warning("Invalid JWT audience")
                raise ValueError("Invalid token audience")
            except jwt.InvalidIssuerError:
                logger.warning("Invalid JWT issuer")
                raise ValueError("Invalid token issuer")
            except jwt.InvalidTokenError:
                logger.warning("Invalid JWT token")
                pass

        # ─── FIXED: Use the correct Supabase function ──────────
        supabase = get_supabase()
        response = supabase.auth.get_user(token)
        if response and response.user:
            return {
                'sub': response.user.id,
                'email': response.user.email,
                'user_metadata': response.user.user_metadata
            }

        raise ValueError("Invalid token")

    except Exception as e:
        logger.error(f"JWT validation error: {e}")
        raise ValueError(f"Token validation failed: {str(e)}")


# ─── DEVICE FINGERPRINTING ────────────────────────────────
def get_device_info() -> Dict[str, Any]:
    """Get device fingerprint from request."""
    user_agent = request.headers.get('User-Agent', 'unknown')
    accept_language = request.headers.get('Accept-Language', 'unknown')
    ip = request.remote_addr

    fingerprint_string = f"{user_agent}|{accept_language}|{ip}"
    device_id = hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]

    return {
        'device_id': device_id,
        'device_name': user_agent[:50] if user_agent else 'Unknown',
        'ip_address': ip,
        'user_agent': user_agent,
        'accept_language': accept_language
    }


# ─── GET USER FROM TOKEN ────────────────────────────────────
def get_user_from_token(token: str) -> dict:
    """Get user data from JWT token with session validation."""
    try:
        payload = validate_jwt(token)
        user_data = {
            'id': payload.get('sub'),
            'email': payload.get('email'),
            'user_metadata': payload.get('user_metadata', {})
        }

        # ─── FIXED: Use the correct Supabase function ──────────
        try:
            supabase = get_supabase()
            response = supabase.table('user_profiles')\
                .select('id, email, role, full_name, is_active, is_verified')\
                .eq('id', user_data['id'])\
                .execute()

            if response.data:
                profile = response.data[0]
                user_data['role'] = profile.get('role', 'user')
                user_data['full_name'] = profile.get('full_name')
                user_data['is_active'] = profile.get('is_active', True)
                user_data['is_verified'] = profile.get('is_verified', False)
                user_data['profile'] = profile
            else:
                user_data['role'] = 'guest'
                user_data['is_active'] = False
                logger.warning(f"User {user_data['id']} not found in database")

        except Exception as e:
            logger.error(f"Database check error: {e}")
            user_data['role'] = 'guest'
            user_data['database_error'] = True

        return user_data

    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        return None


# ─── CHECK PERMISSION ──────────────────────────────────────
def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    if role == 'admin':
        return True

    permissions = ROLE_PERMISSIONS.get(role, [])
    if '*' in permissions:
        return True

    if permission in permissions:
        return True

    role_level = ROLES.get(role, 0)
    for r, level in ROLES.items():
        if level < role_level and permission in ROLE_PERMISSIONS.get(r, []):
            return True

    return False


# ─── AUTH DECORATOR ────────────────────────────────────────
def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Skip auth for public endpoints
            if any(request.path.startswith(p) for p in PUBLIC_ENDPOINTS):
                return f(None, *args, **kwargs)

            if request.method == 'OPTIONS':
                return f(None, *args, **kwargs)

            # ─── IP Validation ──────────────────────────────────
            ip_valid, ip_message = validate_ip(request.remote_addr)
            if not ip_valid:
                logger.warning(f"IP validation failed: {ip_message}")
                AuditLogger.log_event(None, 'ip_blocked', {'ip': request.remote_addr, 'reason': ip_message}, 'failed')
                return jsonify({
                    'error': 'Access denied',
                    'code': 'IP_BLOCKED',
                    'message': ip_message
                }), 403

            # ─── Extract Token ──────────────────────────────────
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                logger.warning(f"Missing Authorization header from {request.remote_addr}")
                AuditLogger.log_event(None, 'auth_missing', {'ip': request.remote_addr}, 'failed')
                return jsonify({
                    'error': 'Missing authorization header',
                    'code': 'AUTH_HEADER_MISSING'
                }), 401

            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                logger.warning(f"Invalid Authorization header format from {request.remote_addr}")
                AuditLogger.log_event(None, 'auth_invalid', {'ip': request.remote_addr}, 'failed')
                return jsonify({
                    'error': 'Invalid authorization header format',
                    'code': 'AUTH_HEADER_INVALID'
                }), 401

            token = parts[1]

            # ─── Session Validation ──────────────────────────────
            session_token = request.headers.get('X-Session-Token')
            if session_token:
                is_valid, session = SessionManager.validate_session(session_token)
                if not is_valid:
                    logger.warning(f"Invalid session token: {session_token[:16]}...")
                    return jsonify({
                        'error': 'Session expired or invalid',
                        'code': 'SESSION_INVALID'
                    }), 401

            # ─── Validate Token ──────────────────────────────────
            try:
                user_data = get_user_from_token(token)
                if not user_data:
                    raise ValueError("Invalid user data")
            except ValueError as e:
                logger.warning(f"Token validation failed: {e}")
                AuditLogger.log_event(None, 'auth_token_invalid', {'error': str(e)}, 'failed')
                return jsonify({
                    'error': 'Invalid or expired token',
                    'code': 'AUTH_TOKEN_INVALID'
                }), 401

            # ─── Check User Status ────────────────────────────────
            if not user_data.get('is_active', True):
                logger.warning(f"Inactive user attempted access: {user_data['id']}")
                AuditLogger.log_event(user_data['id'], 'auth_inactive', {}, 'failed')
                return jsonify({
                    'error': 'Account is deactivated',
                    'code': 'USER_INACTIVE'
                }), 403

            if not user_data.get('is_verified', True):
                logger.warning(f"Unverified user attempted access: {user_data['id']}")
                AuditLogger.log_event(user_data['id'], 'auth_unverified', {}, 'failed')
                return jsonify({
                    'error': 'Email verification required',
                    'code': 'USER_UNVERIFIED'
                }), 403

            # ─── Store user in global context ──────────────────────
            g.user = user_data
            g.user_id = user_data['id']

            # ─── Log successful auth ──────────────────────────────
            AuditLogger.log_event(user_data['id'], 'auth_success', {
                'ip': request.remote_addr,
                'path': request.path
            }, 'success')

            # ─── Pass user to route ──────────────────────────────
            return f(user_data, *args, **kwargs)

        except Exception as e:
            logger.error(f"Auth middleware error: {e}", exc_info=True)
            AuditLogger.log_event(None, 'auth_error', {'error': str(e)}, 'failed')
            return jsonify({
                'error': 'Authentication failed',
                'code': 'AUTH_FAILED'
            }), 500

    return decorated_function


# ─── ADMIN REQUIRED DECORATOR ──────────────────────────────
def require_admin(f):
    """Decorator to require admin role."""
    @wraps(f)
    @require_auth
    def decorated_function(user, *args, **kwargs):
        if not user or user.get('role') != 'admin':
            logger.warning(f"Admin access denied for {user.get('id') if user else 'unknown'}")
            AuditLogger.log_event(user.get('id') if user else None, 'admin_denied', {
                'path': request.path,
                'role': user.get('role') if user else 'none'
            }, 'failed')
            return jsonify({
                'error': 'Admin privileges required',
                'code': 'AUTH_ADMIN_REQUIRED'
            }), 403

        return f(user, *args, **kwargs)

    return decorated_function


# ─── PERMISSION REQUIRED DECORATOR ─────────────────────────
def require_permission(permission: str):
    """Decorator to require a specific permission."""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(user, *args, **kwargs):
            role = user.get('role', 'user')
            if not has_permission(role, permission):
                logger.warning(f"Permission denied for {user['id']}: {permission}")
                AuditLogger.log_event(user['id'], 'permission_denied', {
                    'permission': permission,
                    'role': role,
                    'path': request.path
                }, 'failed')
                return jsonify({
                    'error': f'Permission {permission} required',
                    'code': 'AUTH_PERMISSION_DENIED'
                }), 403

            return f(user, *args, **kwargs)

        return decorated_function

    return decorator


# ─── OPTIONAL AUTH DECORATOR ──────────────────────────────
def optional_auth(f):
    """Decorator that tries auth but doesn't require it."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if auth_header:
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    user_data = get_user_from_token(parts[1])
                    if user_data:
                        g.user = user_data
                        g.user_id = user_data['id']
                        return f(user_data, *args, **kwargs)

            return f(None, *args, **kwargs)

        except Exception as e:
            logger.warning(f"Optional auth failed: {e}")
            return f(None, *args, **kwargs)

    return decorated_function


# ─── RATE LIMIT KEY FUNCTION ──────────────────────────────
def get_user_rate_limit_key():
    """Get rate limit key based on authenticated user."""
    user_id = getattr(g, 'user_id', None)
    if user_id:
        return f"user:{user_id}"

    try:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                user_data = get_user_from_token(parts[1])
                if user_data and user_data.get('id'):
                    return f"user:{user_data['id']}"
    except:
        pass

    return f"ip:{request.remote_addr}"
