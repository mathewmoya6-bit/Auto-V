# app/core/security.py (ADDITIONS)
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status, Request

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================
# TOKEN HASHING FUNCTIONS
# ============================================

def hash_token(token: str) -> str:
    """Hash a token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()

def verify_token_hash(token: str, token_hash: str) -> bool:
    """Verify a token against its hash"""
    return hash_token(token) == token_hash

# ============================================
# JWT TOKEN FUNCTIONS
# ============================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None

# ============================================
# JWT BEARER AUTHENTICATION
# ============================================

class JWTBearer(HTTPBearer):
    """JWT authentication middleware"""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request):
        credentials = await super().__call__(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        token = credentials.credentials
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Attach user info to request state
        request.state.user_id = payload.get("sub") or payload.get("user_id")
        request.state.user_email = payload.get("email")
        request.state.user_role = payload.get("role")
        
        # Check if token is blacklisted
        # This would be checked against token_blacklist table
        
        return credentials

# ============================================
# PASSWORD FUNCTIONS
# ============================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {str(e)}")
        raise

def validate_password_strength(password: str) -> bool:
    """Validate password strength"""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

# ============================================
# EMAIL VERIFICATION TOKENS
# ============================================

def generate_verification_token(user_id: str, email: str) -> str:
    """Generate email verification token"""
    token_data = {
        'user_id': user_id,
        'sub': user_id,  # For consistency with JWTBearer
        'email': email,
        'type': 'email_verification',
        'exp': (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
    return create_access_token(token_data, timedelta(hours=24))

def generate_password_reset_token(user_id: str, email: str) -> str:
    """Generate password reset token"""
    token_data = {
        'user_id': user_id,
        'sub': user_id,  # For consistency with JWTBearer
        'email': email,
        'type': 'password_reset',
        'exp': (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }
    return create_access_token(token_data, timedelta(hours=1))

# ============================================
# ROLE PERMISSIONS
# ============================================

ROLE_PERMISSIONS = {
    'admin': ['*'],
    'valuer': [
        'read:vehicles',
        'create:valuations',
        'read:valuations',
        'update:valuations',
        'read:reports',
        'create:reports'
    ],
    'corporate': [
        'read:vehicles',
        'create:vehicles',
        'update:vehicles',
        'read:valuations',
        'read:reports',
        'read:payments'
    ],
    'dealer': [
        'read:vehicles',
        'create:vehicles',
        'update:vehicles',
        'delete:vehicles',
        'read:valuations',
        'read:reports'
    ],
    'user': [
        'read:profile',
        'update:profile',
        'read:vehicles',
        'create:vehicles',
        'update:vehicles',
        'delete:vehicles',
        'read:valuations',
        'create:valuations',
        'read:payments',
        'create:payments',
        'read:reports'
    ]
}

def check_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission"""
    if role not in ROLE_PERMISSIONS:
        return False
    
    user_permissions = ROLE_PERMISSIONS[role]
    if '*' in user_permissions:
        return True
    
    return permission in user_permissions
