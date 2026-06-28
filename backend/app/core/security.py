# app/core/security.py
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status, Request

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ============================================
# PASSWORD CONTEXT
# ============================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS
)

# ============================================
# TOKEN HASHING FUNCTIONS
# ============================================

def hash_token(token: str) -> str:
    """
    Hash a token for secure storage in database
    
    Args:
        token: The token string to hash
        
    Returns:
        SHA256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()

def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Verify a token against its stored hash
    
    Args:
        token: The token to verify
        token_hash: The stored hash to compare against
        
    Returns:
        True if the token matches the hash, False otherwise
    """
    return hash_token(token) == token_hash

# ============================================
# JWT TOKEN FUNCTIONS
# ============================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Dictionary with user data to encode
        expires_delta: Optional custom expiration time
        
    Returns:
        JWT token string
    """
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
    
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token
    
    Args:
        data: Dictionary with user data to encode
        
    Returns:
        JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload if valid, None otherwise
    """
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
# EMAIL VERIFICATION TOKENS
# ============================================

def generate_verification_token(user_id: str, email: str) -> str:
    """
    Generate email verification token
    
    Args:
        user_id: User ID
        email: User email address
        
    Returns:
        JWT token for email verification
    """
    token_data = {
        "sub": user_id,
        "user_id": user_id,
        "email": email,
        "type": "email_verification",
        "exp": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
    return create_access_token(token_data, timedelta(hours=24))

def generate_password_reset_token(user_id: str, email: str) -> str:
    """
    Generate password reset token
    
    Args:
        user_id: User ID
        email: User email address
        
    Returns:
        JWT token for password reset
    """
    token_data = {
        "sub": user_id,
        "user_id": user_id,
        "email": email,
        "type": "password_reset",
        "exp": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }
    return create_access_token(token_data, timedelta(hours=1))

# ============================================
# PASSWORD FUNCTIONS
# ============================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Stored password hash
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hashed password
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {str(e)}")
        raise

def validate_password_strength(password: str) -> bool:
    """
    Validate password strength requirements
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    
    Args:
        password: Password to validate
        
    Returns:
        True if password meets requirements, False otherwise
    """
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

def generate_random_password(length: int = 16) -> str:
    """
    Generate a secure random password
    
    Args:
        length: Password length (default: 16)
        
    Returns:
        Random password string
    """
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ============================================
# ROLE PERMISSIONS
# ============================================

ROLE_PERMISSIONS = {
    "admin": [
        "*"  # All permissions
    ],
    "manager": [
        "users.read",
        "users.write",
        "users.delete",
        "vehicles.read",
        "vehicles.write",
        "valuations.read",
        "valuations.write",
        "reports.read",
        "reports.write",
        "payments.read",
        "audit.read"
    ],
    "valuator": [
        "vehicles.read",
        "valuations.create",
        "valuations.read",
        "valuations.update",
        "reports.create",
        "reports.read"
    ],
    "corporate": [
        "vehicles.read",
        "vehicles.create",
        "vehicles.update",
        "valuations.read",
        "reports.read",
        "payments.read"
    ],
    "dealer": [
        "vehicles.read",
        "vehicles.create",
        "vehicles.update",
        "vehicles.delete",
        "valuations.read",
        "reports.read"
    ],
    "user": [
        "profile.read",
        "profile.update",
        "vehicles.read",
        "vehicles.create",
        "vehicles.update",
        "vehicles.delete",
        "valuations.read",
        "valuations.create",
        "payments.read",
        "payments.create",
        "reports.read"
    ]
}

def check_permission(role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission
    
    Args:
        role: User role string
        permission: Permission string to check
        
    Returns:
        True if role has permission, False otherwise
    """
    permissions = ROLE_PERMISSIONS.get(role, [])
    
    # Admin has all permissions
    if "*" in permissions:
        return True
    
    return permission in permissions

def get_role_permissions(role: str) -> List[str]:
    """
    Get all permissions for a role
    
    Args:
        role: User role string
        
    Returns:
        List of permission strings
    """
    return ROLE_PERMISSIONS.get(role, [])

# ============================================
# JWT BEARER AUTHENTICATION
# ============================================

class JWTBearer(HTTPBearer):
    """
    JWT Bearer authentication middleware
    
    Validates JWT token and attaches user info to request state
    """
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request):
        """
        Validate JWT token from Authorization header
        
        Args:
            request: FastAPI request object
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        credentials = await super().__call__(request)
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = credentials.credentials
        payload = decode_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Attach user info to request state
        request.state.user_id = payload.get("sub") or payload.get("user_id")
        request.state.user_email = payload.get("email")
        request.state.user_role = payload.get("role", "user")
        request.state.token_payload = payload
        
        # Check token type if present
        token_type = payload.get("type")
        if token_type == "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token cannot be used for authentication",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return payload

# ============================================
# ROLE-BASED ACCESS CONTROL
# ============================================

def require_permission(permission: str):
    """
    Dependency for role-based permission checking
    
    Args:
        permission: Required permission string
        
    Returns:
        Callable that checks permission on request
    """
    async def permission_checker(
        request: Request,
        token_data: dict = Depends(JWTBearer())
    ):
        role = request.state.user_role
        if not check_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        return True
    
    return permission_checker

def require_role(required_role: str):
    """
    Dependency for role-based access control
    
    Args:
        required_role: Required role string
        
    Returns:
        Callable that checks role on request
    """
    async def role_checker(
        request: Request,
        token_data: dict = Depends(JWTBearer())
    ):
        role = request.state.user_role
        
        # Admin can access everything
        if role == "admin":
            return True
        
        if role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return True
    
    return role_checker

# ============================================
# CSRF PROTECTION
# ============================================

def generate_csrf_token() -> str:
    """
    Generate a secure CSRF token
    
    Returns:
        Random CSRF token string
    """
    return secrets.token_urlsafe(32)

def validate_csrf_token(token: str, stored_token: str) -> bool:
    """
    Validate a CSRF token
    
    Args:
        token: Token to validate
        stored_token: Stored token to compare against
        
    Returns:
        True if token is valid, False otherwise
    """
    if not token or not stored_token:
        return False
    return secrets.compare_digest(token, stored_token)

# ============================================
# API KEY GENERATION
# ============================================

def generate_api_key() -> str:
    """
    Generate a secure API key
    
    Returns:
        API key string in format: av_XXXXXXXXXXXXX
    """
    prefix = "av"
    random_part = secrets.token_urlsafe(24)
    return f"{prefix}_{random_part}"

def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage
    
    Args:
        api_key: API key string
        
    Returns:
        SHA256 hash of the API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()

# ============================================
# SESSION TOKEN FUNCTIONS
# ============================================

def generate_session_id() -> str:
    """
    Generate a unique session ID
    
    Returns:
        Random session ID string
    """
    return secrets.token_urlsafe(32)

def validate_session(session_id: str, user_id: str) -> bool:
    """
    Validate a session ID for a user
    
    Args:
        session_id: Session ID to validate
        user_id: User ID to check against
        
    Returns:
        True if session is valid, False otherwise
    """
    # This would typically check against a session store
    # Placeholder implementation
    return True
