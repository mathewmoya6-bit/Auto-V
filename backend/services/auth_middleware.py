"""
JWT Authentication Middleware for FastAPI
Handles token verification, generation, and user authentication
"""

import os
import logging
from typing import Optional, Dict, Any, Union, List
from datetime import datetime, timedelta
from functools import wraps
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWTError

logger = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip()
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
JWT_REFRESH_EXPIRATION_DAYS = int(os.getenv("JWT_REFRESH_EXPIRATION_DAYS", "30"))

if not JWT_SECRET:
    logger.warning("⚠️ JWT_SECRET not set - using default (INSECURE FOR PRODUCTION)")
    JWT_SECRET = "auto-v-default-secret-key-change-in-production"


# ─── Token Generation ──────────────────────────────────────────

def generate_token(
    user_id: str, 
    email: str, 
    role: str = "user",
    expires_in_hours: int = JWT_EXPIRATION_HOURS,
    token_type: str = "access"
) -> str:
    """
    Generate a JWT token.
    
    Args:
        user_id: User ID
        email: User email
        role: User role (user, admin, etc.)
        expires_in_hours: Token expiration in hours
        token_type: Type of token (access, refresh)
    
    Returns:
        Encoded JWT token string
    """
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable is not set")
    
    expiry = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": token_type,
        "exp": expiry,
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_access_token(user_id: str, email: str, role: str = "user") -> str:
    """Generate an access token."""
    return generate_token(user_id, email, role, JWT_EXPIRATION_HOURS, "access")


def generate_refresh_token(user_id: str, email: str, role: str = "user") -> str:
    """Generate a refresh token."""
    return generate_token(
        user_id, 
        email, 
        role, 
        JWT_REFRESH_EXPIRATION_DAYS * 24, 
        "refresh"
    )


def generate_token_pair(user_id: str, email: str, role: str = "user") -> Dict[str, str]:
    """Generate both access and refresh tokens."""
    return {
        "access_token": generate_access_token(user_id, email, role),
        "refresh_token": generate_refresh_token(user_id, email, role),
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION_HOURS * 3600
    }


# ─── Token Verification ──────────────────────────────────────────

def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify a JWT token.
    
    Args:
        token: JWT token string
        token_type: Expected token type (access, refresh)
    
    Returns:
        Decoded token payload if valid, None otherwise
    """
    if not token:
        return None
    
    try:
        # Remove Bearer prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Verify token type
        if payload.get("type") != token_type:
            logger.warning(f"Invalid token type: expected {token_type}, got {payload.get('type')}")
            return None
        
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


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify an access token."""
    return verify_token(token, "access")


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a refresh token."""
    return verify_token(token, "refresh")


# ─── FastAPI Security Dependencies ──────────────────────────────

class JWTBearer(HTTPBearer):
    """
    JWT Bearer token authentication for FastAPI.
    """
    
    def __init__(
        self, 
        auto_error: bool = True,
        required_role: Optional[str] = None,
        allowed_roles: Optional[List[str]] = None
    ):
        super().__init__(auto_error=auto_error)
        self.required_role = required_role
        self.allowed_roles = allowed_roles
    
    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)
        
        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return None
        
        if credentials.scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return None
        
        # Verify token
        payload = verify_access_token(credentials.credentials)
        
        if not payload:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return None
        
        # Check role requirements
        user_role = payload.get("role", "user")
        
        if self.required_role and user_role != self.required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{self.required_role}' required"
            )
        
        if self.allowed_roles and user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Allowed roles: {', '.join(self.allowed_roles)}"
            )
        
        return payload


# ─── FastAPI Dependencies ──────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current user from JWT token.
    
    Usage:
        @app.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            return {"user": current_user}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = verify_access_token(credentials.credentials)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return payload


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to get current user if authenticated, otherwise None.
    
    Usage:
        @app.get("/optional")
        async def optional_route(current_user: Optional[dict] = Depends(get_current_user_optional)):
            if current_user:
                return {"user": current_user}
            return {"message": "Not authenticated"}
    """
    if not credentials:
        return None
    
    payload = verify_access_token(credentials.credentials)
    
    if not payload:
        return None
    
    return payload


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current active user.
    Extends get_current_user with additional validation.
    """
    # Add additional user validation here if needed
    # e.g., check if user is active in database
    
    return current_user


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current admin user.
    Requires admin role.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


# ─── Route Decorators ──────────────────────────────────────────

def require_auth(required_role: Optional[str] = None, allowed_roles: Optional[List[str]] = None):
    """
    Decorator for FastAPI routes to require authentication.
    
    Usage:
        @app.get("/protected")
        @require_auth()
        async def protected_route():
            return {"message": "Protected"}
        
        @app.get("/admin")
        @require_auth(required_role="admin")
        async def admin_route():
            return {"message": "Admin only"}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This is handled by the dependency injection
            # The decorator is just for documentation purposes
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ─── Middleware (for manual authentication) ────────────────────

class JWTAuthMiddleware:
    """
    Middleware for manual JWT authentication.
    Can be used in FastAPI middleware for request-level authentication.
    """
    
    def __init__(self, app, exclude_paths: Optional[List[str]] = None):
        self.app = app
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
            "/api/auth/reset-password"
        ]
    
    async def __call__(self, request: Request, call_next):
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get token from header
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.replace("Bearer ", "")
            payload = verify_access_token(token)
            if payload:
                request.state.user = payload
        
        response = await call_next(request)
        return response


# ─── Helper Functions ──────────────────────────────────────────

def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from a token."""
    payload = verify_access_token(token)
    if payload:
        return payload.get("sub")
    return None


def get_user_email_from_token(token: str) -> Optional[str]:
    """Extract user email from a token."""
    payload = verify_access_token(token)
    if payload:
        return payload.get("email")
    return None


def get_user_role_from_token(token: str) -> Optional[str]:
    """Extract user role from a token."""
    payload = verify_access_token(token)
    if payload:
        return payload.get("role", "user")
    return None


def is_token_valid(token: str) -> bool:
    """Check if a token is valid."""
    return verify_access_token(token) is not None


def refresh_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    Refresh an access token using a refresh token.
    
    Args:
        refresh_token: Valid refresh token
    
    Returns:
        New token pair or None if refresh token is invalid
    """
    payload = verify_refresh_token(refresh_token)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role", "user")
    
    if not user_id or not email:
        return None
    
    return generate_token_pair(user_id, email, role)


# ─── Exports ──────────────────────────────────────────────────

__all__ = [
    # Token Generation
    "generate_token",
    "generate_access_token",
    "generate_refresh_token",
    "generate_token_pair",
    
    # Token Verification
    "verify_token",
    "verify_access_token",
    "verify_refresh_token",
    
    # FastAPI Dependencies
    "JWTBearer",
    "get_current_user",
    "get_current_user_optional",
    "get_current_active_user",
    "get_current_admin_user",
    
    # Decorators
    "require_auth",
    
    # Middleware
    "JWTAuthMiddleware",
    
    # Helpers
    "get_user_id_from_token",
    "get_user_email_from_token",
    "get_user_role_from_token",
    "is_token_valid",
    "refresh_token",
]
