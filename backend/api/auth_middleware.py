# services/auth_middleware.py - Production Ready v2

import os
import logging
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, jsonify, g
import jwt
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─── ENV CONFIG ─────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip()
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

if not JWT_SECRET:
    logger.warning("⚠️ JWT_SECRET environment variable is not set!")

# ─── TOKEN VERIFICATION ──────────────────────────────────

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a JWT token and return the payload if valid.
    Returns None if token is invalid or expired.
    """
    if not token:
        return None
    
    try:
        # Remove "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        
        return payload
    
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get the current authenticated user from the request context.
    Must be called after verify_token or require_auth has been used.
    Returns user data from token payload.
    """
    if hasattr(g, 'user') and g.user:
        return g.user
    return None


def require_auth(func):
    """
    Decorator to require authentication for a route.
    Will return 401 Unauthorized if token is invalid or missing.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header:
            return jsonify({
                "error": "Missing authorization header",
                "message": "Authorization header is required"
            }), 401
        
        # Verify token
        payload = verify_token(auth_header)
        
        if not payload:
            return jsonify({
                "error": "Invalid or expired token",
                "message": "Please authenticate again"
            }), 401
        
        # Store user info in flask.g for use in route
        g.user = {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "role": payload.get("role", "user"),
            "expires": payload.get("exp")
        }
        
        # Also set user_id for convenience
        g.user_id = payload.get("user_id")
        
        return func(*args, **kwargs)
    
    return wrapper


def optional_auth(func):
    """
    Decorator for optional authentication.
    Will not reject unauthenticated requests, but will set g.user if valid.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header:
            payload = verify_token(auth_header)
            if payload:
                g.user = {
                    "user_id": payload.get("user_id"),
                    "email": payload.get("email"),
                    "role": payload.get("role", "user"),
                    "expires": payload.get("exp")
                }
                g.user_id = payload.get("user_id")
        
        return func(*args, **kwargs)
    
    return wrapper


# ─── TOKEN GENERATION ─────────────────────────────────

def generate_token(user_id: str, email: str, role: str = "user") -> str:
    """
    Generate a new JWT token for a user.
    """
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable is not set")
    
    expiry = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": expiry,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    
    return token


def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Supabase JWT token.
    Supabase tokens are standard JWT tokens that can be verified
    with the Supabase JWT secret.
    """
    return verify_token(token)


__all__ = [
    "verify_token",
    "require_auth",
    "optional_auth",
    "get_current_user",
    "generate_token",
    "verify_supabase_token"
]
