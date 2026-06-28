# security.py - AUTO-V Security Module
import os
import re
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    verify_jwt_in_request,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies
)
import bcrypt
import jwt
from config import config

logger = logging.getLogger(__name__)

# ─── JWT ──────────────────────────────────────────────────────────

def generate_tokens(user_id: str, user_data: Dict[str, Any] = None) -> Dict[str, str]:
    """
    Generate JWT access and refresh tokens.
    
    Args:
        user_id: User ID
        user_data: Additional user data to include in token
        
    Returns:
        Dict with access_token and refresh_token
    """
    additional_claims = user_data or {}
    additional_claims['user_id'] = user_id
    
    access_token = create_access_token(
        identity=user_id,
        additional_claims=additional_claims,
        expires_delta=timedelta(seconds=config.JWT_ACCESS_TOKEN_EXPIRES)
    )
    
    refresh_token = create_refresh_token(
        identity=user_id,
        expires_delta=timedelta(seconds=config.JWT_REFRESH_TOKEN_EXPIRES)
    )
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        Decoded token payload or None
    """
    try:
        return jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM]
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None

def get_current_user():
    """Get current user from JWT token."""
    try:
        verify_jwt_in_request()
        return get_jwt_identity()
    except Exception:
        return None

def get_current_user_data() -> Dict[str, Any]:
    """Get current user data from JWT token."""
    try:
        verify_jwt_in_request()
        return get_jwt()
    except Exception:
        return {}

# ─── Password Hashing ───────────────────────────────────────────

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

# ─── CSRF Protection ────────────────────────────────────────────

def generate_csrf_token() -> str:
    """
    Generate a CSRF token.
    
    Returns:
        CSRF token string
    """
    return secrets.token_urlsafe(32)

def validate_csrf_token(token: str, session_token: str) -> bool:
    """
    Validate CSRF token.
    
    Args:
        token: Token from request
        session_token: Token from session
        
    Returns:
        True if valid, False otherwise
    """
    return token and session_token and secrets.compare_digest(token, session_token)

# ─── Rate Limiting ──────────────────────────────────────────────

class RateLimiter:
    """In-memory rate limiter (fallback when Redis is not available)."""
    
    def __init__(self):
        self.requests = {}
        self.limit = 100
        self.window = 60  # seconds
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed.
        
        Args:
            key: Rate limit key (usually IP or user ID)
            
        Returns:
            True if allowed, False if rate limit exceeded
        """
        now = datetime.now().timestamp()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old requests
        self.requests[key] = [
            t for t in self.requests[key]
            if now - t < self.window
        ]
        
        if len(self.requests[key]) >= self.limit:
            return False
        
        self.requests[key].append(now)
        return True

# ─── Input Validation ───────────────────────────────────────────

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent XSS and injection.
    
    Args:
        text: Input text
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove script tags
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
    
    # Escape special characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#x27;')
    
    return text.strip()

def validate_email(email: str) -> bool:
    """
    Validate email address.
    
    Args:
        email: Email address
        
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """
    Validate phone number.
    
    Args:
        phone: Phone number
        
    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False
    
    # Remove common separators
    phone = re.sub(r'[\s\-\(\)\.]', '', phone)
    
    # Kenya format: 0712345678, 254712345678, +254712345678
    pattern = r'^(0|254|\+254)?[17]\d{8}$'
    return bool(re.match(pattern, phone))

def validate_vin(vin: str) -> bool:
    """
    Validate VIN number.
    
    Args:
        vin: VIN number
        
    Returns:
        True if valid, False otherwise
    """
    if not vin:
        return False
    
    vin = vin.upper().strip()
    
    # Must be 17 characters
    if len(vin) != 17:
        return False
    
    # Cannot contain I, O, Q
    if re.search(r'[IOQ]', vin):
        return False
    
    # Must be alphanumeric
    if not vin.isalnum():
        return False
    
    return True

# ─── SQL Injection Prevention ───────────────────────────────────

def escape_sql_string(text: str) -> str:
    """
    Escape SQL string to prevent injection.
    
    Args:
        text: Input text
        
    Returns:
        Escaped string
    """
    if not text:
        return ""
    
    # Replace single quotes with double quotes
    return text.replace("'", "''")

def is_safe_sql_input(text: str) -> bool:
    """
    Check if input is safe for SQL.
    
    Args:
        text: Input text
        
    Returns:
        True if safe, False otherwise
    """
    if not text:
        return True
    
    # Check for SQL injection patterns
    patterns = [
        r'(\bSELECT\b.*\bFROM\b)',
        r'(\bINSERT\b.*\bINTO\b)',
        r'(\bUPDATE\b.*\bSET\b)',
        r'(\bDELETE\b.*\bFROM\b)',
        r'(\bDROP\b.*\bTABLE\b)',
        r'(\bUNION\b.*\bSELECT\b)',
        r'(\bOR\b.*\b1=1\b)',
        r'(\b;.*\bDROP\b)',
    ]
    
    text_upper = text.upper()
    for pattern in patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            return False
    
    return True

# ─── Session Management ─────────────────────────────────────────

def generate_session_id() -> str:
    """
    Generate a secure session ID.
    
    Returns:
        Session ID string
    """
    return secrets.token_urlsafe(32)

def generate_otp(length: int = 6) -> str:
    """
    Generate a one-time password.
    
    Args:
        length: OTP length
        
    Returns:
        OTP string
    """
    return ''.join(secrets.choice('0123456789') for _ in range(length))

def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        API key string
    """
    return f"ak_{secrets.token_urlsafe(32)}"

# ─── Request Validation ─────────────────────────────────────────

def validate_request_data(data: Dict[str, Any], required_fields: list) -> Tuple[bool, Optional[str]]:
    """
    Validate required fields in request data.
    
    Args:
        data: Request data
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    missing = [field for field in required_fields if not data.get(field)]
    
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    return True, None

def validate_content_type(content_type: str, allowed_types: list) -> bool:
    """
    Validate content type.
    
    Args:
        content_type: Content type header
        allowed_types: List of allowed content types
        
    Returns:
        True if valid, False otherwise
    """
    return content_type in allowed_types

# ─── File Security ──────────────────────────────────────────────

def is_safe_filename(filename: str) -> bool:
    """
    Check if filename is safe.
    
    Args:
        filename: File name
        
    Returns:
        True if safe, False otherwise
    """
    if not filename:
        return False
    
    # Check for path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check for dangerous extensions
    dangerous_extensions = [
        '.exe', '.bat', '.cmd', '.sh', '.php', '.pl', '.py',
        '.js', '.vbs', '.ps1', '.jar', '.war', '.ear'
    ]
    
    filename_lower = filename.lower()
    for ext in dangerous_extensions:
        if filename_lower.endswith(ext):
            return False
    
    return True

def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.
    
    Args:
        filename: File name
        
    Returns:
        File extension in lowercase
    """
    if not filename or '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[-1].lower()

def is_allowed_image_type(filename: str) -> bool:
    """
    Check if file is an allowed image type.
    
    Args:
        filename: File name
        
    Returns:
        True if allowed, False otherwise
    """
    allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif']
    ext = get_file_extension(filename)
    return ext in allowed_extensions

def is_allowed_document_type(filename: str) -> bool:
    """
    Check if file is an allowed document type.
    
    Args:
        filename: File name
        
    Returns:
        True if allowed, False otherwise
    """
    allowed_extensions = ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt']
    ext = get_file_extension(filename)
    return ext in allowed_extensions

# ─── IP Address Security ─────────────────────────────────────────

def is_private_ip(ip: str) -> bool:
    """
    Check if IP address is private.
    
    Args:
        ip: IP address
        
    Returns:
        True if private, False otherwise
    """
    if not ip:
        return True
    
    # Private IP ranges
    private_ranges = [
        r'^10\.',           # 10.0.0.0/8
        r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',  # 172.16.0.0/12
        r'^192\.168\.',     # 192.168.0.0/16
        r'^127\.',          # 127.0.0.0/8
        r'^0\.',            # 0.0.0.0/8
        r'^::1$',           # IPv6 loopback
        r'^fe80:',          # IPv6 link-local
    ]
    
    for pattern in private_ranges:
        if re.match(pattern, ip):
            return True
    
    return False

def get_client_ip() -> str:
    """
    Get client IP address from request.
    
    Returns:
        Client IP address
    """
    # Check for forwarded IP
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    
    # Check for real IP
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    
    # Fallback to remote address
    return request.remote_addr or '0.0.0.0'

# ─── User Agent Security ────────────────────────────────────────

def is_bot_user_agent(user_agent: str) -> bool:
    """
    Check if user agent is a bot.
    
    Args:
        user_agent: User agent string
        
    Returns:
        True if bot, False otherwise
    """
    if not user_agent:
        return True
    
    bot_patterns = [
        'bot', 'crawler', 'spider', 'scraper', 'scan',
        'headless', 'selenium', 'puppeteer', 'phantom',
        'curl', 'wget', 'python-requests', 'go-http'
    ]
    
    user_agent_lower = user_agent.lower()
    for pattern in bot_patterns:
        if pattern in user_agent_lower:
            return True
    
    return False

# ─── CORS Security ──────────────────────────────────────────────

def is_allowed_origin(origin: str) -> bool:
    """
    Check if origin is allowed for CORS.
    
    Args:
        origin: Origin header
        
    Returns:
        True if allowed, False otherwise
    """
    if not origin:
        return False
    
    allowed_origins = config.ALLOWED_ORIGINS
    
    # Allow localhost in development
    if config.DEBUG and origin.startswith('http://localhost'):
        return True
    
    return origin in allowed_origins

# ─── Security Headers ────────────────────────────────────────────

def get_security_headers() -> Dict[str, str]:
    """
    Get security headers for responses.
    
    Returns:
        Dict of security headers
    """
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:;",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Server': 'AUTO-V'
    }

# ─── Quick Test ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing Security Module...")
    
    # Test password hashing
    password = "SecurePassword123!"
    hashed = hash_password(password)
    print(f"✅ Password hashed: {hashed[:20]}...")
    
    # Test verification
    verified = verify_password(password, hashed)
    print(f"✅ Password verified: {verified}")
    
    # Test email validation
    emails = ["test@example.com", "invalid-email"]
    for email in emails:
        result = validate_email(email)
        print(f"✅ Email '{email}': {result}")
    
    # Test VIN validation
    vins = ["1HGCM82633A123456", "INVALID"]
    for vin in vins:
        result = validate_vin(vin)
        print(f"✅ VIN '{vin}': {result}")
    
    # Test CSRF token
    token = generate_csrf_token()
    print(f"✅ CSRF token: {token[:20]}...")
    
    # Test API key
    api_key = generate_api_key()
    print(f"✅ API key: {api_key[:20]}...")
    
    print("✅ Security module test complete")
