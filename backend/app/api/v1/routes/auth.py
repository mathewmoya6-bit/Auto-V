# app/api/v1/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
import hashlib
import hmac
import secrets
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    verify_password, get_password_hash, validate_password_strength,
    JWTBearer, hash_token, verify_token_hash,
    generate_verification_token, generate_password_reset_token,
    ROLE_PERMISSIONS, check_permission
)
from app.core.logging import get_logger
from app.core.cache import Cache
from app.services.email_service import EmailService
from app.models.user import (
    UserCreate, UserLogin, TokenResponse, UserResponse,
    UserProfile, PasswordResetRequest, PasswordResetConfirm,
    EmailVerificationRequest, ChangePasswordRequest,
    LogoutRequest, TokenRevokeRequest
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

logger = get_logger(__name__)
cache = Cache()
email_service = EmailService()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

# ============================================
# REQUEST MODELS
# ============================================

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    accept_terms: bool = True
    referral_code: Optional[str] = None
    
    @validator('password')
    def validate_password_strength(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be at least 8 characters with uppercase, "
                "lowercase, number, and special character"
            )
        return v
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if v:
            v = v.replace(' ', '').replace('+', '')
            if not v.startswith('254') and not v.startswith('0'):
                raise ValueError('Phone number must start with 254 or 0')
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: Optional[str] = None
    device_name: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=50)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be at least 8 characters with uppercase, "
                "lowercase, number, and special character"
            )
        return v

class EmailVerificationRequest(BaseModel):
    token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=50)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be at least 8 characters with uppercase, "
                "lowercase, number, and special character"
            )
        return v

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    all_devices: bool = False

class TokenRevokeRequest(BaseModel):
    token: str
    token_type: str = "access"

# ============================================
# HELPER FUNCTIONS
# ============================================

async def create_audit_log(
    db,
    user_id: Optional[str],
    action: str,
    details: Dict[str, Any],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Create audit log entry"""
    try:
        audit_entry = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'action': action,
            'details': details,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': datetime.utcnow().isoformat()
        }
        db.table('audit_logs').insert(audit_entry).execute()
    except Exception as e:
        logger.error(f"Failed to create audit log: {str(e)}")

async def check_rate_limit(identifier: str, limit: int = 5, window: int = 300):
    """Check rate limit for an identifier"""
    key = f"rate_limit:{identifier}"
    count = await cache.get(key)
    
    if count and int(count) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Please try again in {window} seconds"
        )
    
    if count:
        await cache.increment(key)
    else:
        await cache.set(key, "1", window)
    
    return True

async def send_verification_email(email: str, name: str, token: str):
    """Send email verification email"""
    try:
        await email_service.send_verification_email(
            to_email=email,
            name=name,
            token=token
        )
        logger.info(f"Verification email sent to: {email}")
    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")

async def send_password_reset_email(email: str, name: str, token: str):
    """Send password reset email"""
    try:
        await email_service.send_password_reset_email(
            to_email=email,
            name=name,
            token=token
        )
        logger.info(f"Password reset email sent to: {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@router.get("/")
async def auth_root():
    """Authentication service status endpoint"""
    return {
        "service": "AUTO-V Authentication",
        "status": "online",
        "version": settings.APP_VERSION,
        "features": {
            "registration": True,
            "login": True,
            "email_verification": True,
            "password_reset": True,
            "two_factor_auth": False,
            "sso": False
        }
    }

@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    Register a new user account
    
    - Validates email uniqueness
    - Validates password strength
    - Creates user account
    - Sends verification email
    - Creates audit log
    """
    try:
        # Check rate limit
        await check_rate_limit(f"register:{user_data.email}", limit=3, window=600)
        
        # Check if user exists
        existing_user = db.table('users').select('*').eq('email', user_data.email).execute()
        if existing_user.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check phone number if provided
        if user_data.phone_number:
            existing_phone = db.table('users').select('*').eq('phone_number', user_data.phone_number).execute()
            if existing_phone.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Split full name
        name_parts = user_data.full_name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Create user
        user_id = str(uuid.uuid4())
        new_user = {
            'id': user_id,
            'email': user_data.email,
            'password_hash': hashed_password,
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': user_data.phone_number,
            'role': 'user',
            'email_verified': False,
            'is_active': True,
            'accept_terms': user_data.accept_terms,
            'referral_code': user_data.referral_code,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = db.table('users').insert(new_user).execute()
        
        # Create user profile
        profile = {
            'user_id': user_id,
            'profile_picture': None,
            'company': None,
            'address': None,
            'preferences': {},
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        db.table('user_profiles').insert(profile).execute()
        
        # Generate verification token
        verification_token = generate_verification_token(user_id, user_data.email)
        
        # Store verification token in database
        db.table('email_verifications').insert({
            'user_id': user_id,
            'token': verification_token,
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        # Send verification email in background
        background_tasks.add_task(
            send_verification_email,
            user_data.email,
            user_data.full_name,
            verification_token
        )
        
        # Create audit log
        await create_audit_log(
            db,
            user_id,
            'user_registered',
            {
                'email': user_data.email,
                'ip': request.client.host if request.client else None
            },
            request.client.host if request.client else None,
            request.headers.get('user-agent')
        )
        
        logger.info(f"User registered successfully: {user_data.email}")
        
        return {
            "success": True,
            "message": "Registration successful. Please verify your email.",
            "user": {
                "id": user_id,
                "email": user_data.email,
                "full_name": user_data.full_name,
                "role": "user",
                "email_verified": False
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    db=Depends(get_db)
):
    """
    Authenticate user and return tokens
    
    - Validates credentials
    - Checks account status
    - Creates access and refresh tokens
    - Logs login attempt
    - Supports device tracking
    """
    try:
        # Check rate limit
        identifier = f"login:{login_data.email}:{request.client.host if request.client else 'unknown'}"
        await check_rate_limit(identifier, limit=5, window=900)
        
        # Find user
        result = db.table('users').select('*').eq('email', login_data.email).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user = result.data[0]
        
        # Check if user is active
        if not user.get('is_active', True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Check if account is locked
        locked_until = user.get('locked_until')
        if locked_until and datetime.fromisoformat(locked_until) > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked until {locked_until}"
            )
        
        # Verify password
        if not verify_password(login_data.password, user.get('password_hash')):
            # Increment failed attempts
            failed_attempts = user.get('failed_login_attempts', 0) + 1
            update_data = {
                'failed_login_attempts': failed_attempts,
                'last_failed_login': datetime.utcnow().isoformat()
            }
            
            # Lock account after 5 failed attempts
            if failed_attempts >= 5:
                update_data['is_active'] = False
                update_data['locked_until'] = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
                
                # Send account locked email
                background_tasks = BackgroundTasks()
                background_tasks.add_task(
                    email_service.send_account_locked_email,
                    user['email'],
                    f"{user.get('first_name', '')} {user.get('last_name', '')}",
                    {
                        'failed_attempts': failed_attempts,
                        'lock_time': datetime.utcnow().isoformat(),
                        'lock_duration': '30 minutes',
                        'ip_address': request.client.host if request.client else None,
                        'location': 'Unknown'
                    }
                )
            
            db.table('users').update(update_data).eq('id', user['id']).execute()
            
            logger.warning(f"Failed login attempt for: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Reset failed attempts on successful login
        db.table('users').update({
            'failed_login_attempts': 0,
            'last_login': datetime.utcnow().isoformat(),
            'last_login_ip': request.client.host if request.client else None,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', user['id']).execute()
        
        # Create tokens
        token_data = {
            "sub": user['id'],
            "email": user['email'],
            "role": user.get('role', 'user'),
            "email_verified": user.get('email_verified', False)
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Store refresh token in database
        refresh_token_hash = hash_token(refresh_token)
        db.table('refresh_tokens').insert({
            'user_id': user['id'],
            'token_hash': refresh_token_hash,
            'device_id': login_data.device_id,
            'device_name': login_data.device_name,
            'ip_address': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
            'expires_at': (datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).isoformat(),
            'created_at': datetime.utcnow().isoformat(),
            'is_revoked': False
        }).execute()
        
        # Create audit log
        await create_audit_log(
            db,
            user['id'],
            'user_login',
            {
                'email': user['email'],
                'ip': request.client.host if request.client else None,
                'device_id': login_data.device_id
            },
            request.client.host if request.client else None,
            request.headers.get('user-agent')
        )
        
        logger.info(f"User logged in: {user['email']}")
        
        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user['id'],
                "email": user['email'],
                "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                "role": user.get('role', 'user'),
                "email_verified": user.get('email_verified', False)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh")
async def refresh_access_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db=Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    - Validates refresh token
    - Implements token rotation
    - Revokes old refresh token
    - Creates new token pair
    """
    try:
        # Decode refresh token
        payload = decode_token(refresh_data.refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        if payload.get('type') != 'refresh':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Check if token is in database and not revoked
        token_hash = hash_token(refresh_data.refresh_token)
        token_result = db.table('refresh_tokens') \
            .select('*') \
            .eq('token_hash', token_hash) \
            .eq('is_revoked', False) \
            .execute()
        
        if not token_result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or revoked"
            )
        
        # Check if token expired
        token_record = token_result.data[0]
        if datetime.fromisoformat(token_record['expires_at']) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        
        # Get user
        user_id = payload.get('sub')
        user_result = db.table('users').select('*').eq('id', user_id).execute()
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        user = user_result.data[0]
        
        # Revoke old refresh token (token rotation)
        db.table('refresh_tokens').update({
            'is_revoked': True,
            'revoked_at': datetime.utcnow().isoformat(),
            'revoked_reason': 'Token rotation'
        }).eq('id', token_record['id']).execute()
        
        # Create new tokens
        token_data = {
            "sub": user['id'],
            "email": user['email'],
            "role": user.get('role', 'user'),
            "email_verified": user.get('email_verified', False)
        }
        
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        # Store new refresh token
        new_token_hash = hash_token(new_refresh_token)
        db.table('refresh_tokens').insert({
            'user_id': user['id'],
            'token_hash': new_token_hash,
            'device_id': token_record.get('device_id'),
            'device_name': token_record.get('device_name'),
            'ip_address': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
            'expires_at': (datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).isoformat(),
            'created_at': datetime.utcnow().isoformat(),
            'is_revoked': False,
            'previous_token_id': token_record['id']
        }).execute()
        
        # Create audit log
        await create_audit_log(
            db,
            user['id'],
            'token_refresh',
            {
                'user_id': user['id'],
                'ip': request.client.host if request.client else None
            },
            request.client.host if request.client else None,
            request.headers.get('user-agent')
        )
        
        logger.info(f"Tokens refreshed for user: {user['email']}")
        
        return {
            "success": True,
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout(
    request: Request,
    logout_data: LogoutRequest,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """
    Logout user
    
    - Revokes refresh token
    - Optionally revokes all device sessions
    - Creates audit log
    """
    try:
        user_id = request.state.user_id
        
        if logout_data.all_devices:
            # Revoke all refresh tokens for user
            db.table('refresh_tokens').update({
                'is_revoked': True,
                'revoked_at': datetime.utcnow().isoformat(),
                'revoked_reason': 'Logout all devices'
            }).eq('user_id', user_id).execute()
        elif logout_data.refresh_token:
            # Revoke specific refresh token
            token_hash = hash_token(logout_data.refresh_token)
            db.table('refresh_tokens').update({
                'is_revoked': True,
                'revoked_at': datetime.utcnow().isoformat(),
                'revoked_reason': 'Logout'
            }).eq('token_hash', token_hash).execute()
        
        # Create audit log
        await create_audit_log(
            db,
            user_id,
            'user_logout',
            {
                'all_devices': logout_data.all_devices,
                'ip': request.client.host if request.client else None
            },
            request.client.host if request.client else None,
            request.headers.get('user-agent')
        )
        
        logger.info(f"User logged out: {request.state.user_email}")
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/verify-email")
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    verification_data: EmailVerificationRequest,
    db=Depends(get_db)
):
    """
    Verify user email address
    
    - Validates verification token
    - Updates user email_verified status
    - Creates audit log
    """
    try:
        # Decode token
        payload = decode_token(verification_data.token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        if payload.get('type') != 'email_verification':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        # Check token in database
        token_result = db.table('email_verifications') \
            .select('*') \
            .eq('token', verification_data.token) \
            .execute()
        
        if not token_result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token not found"
            )
        
        token_record = token_result.data[0]
        
        # Check if token expired
        if datetime.fromisoformat(token_record['expires_at']) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token expired"
            )
        
        # Update user
        user_id = payload.get('sub')
        db.table('users').update({
            'email_verified': True,
            'email_verified_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()
        
        # Mark token as used
        db.table('email_verifications').update({
            'used_at': datetime.utcnow().isoformat()
        }).eq('id', token_record['id']).execute()
        
        # Create audit log
        await create_audit_log(
            db,
            user_id,
            'email_verified',
            {
                'ip': request.client.host if request.client else None
            },
            request.client.host if request.client else None,
            request.headers.get('user-agent')
        )
        
        logger.info(f"Email verified for user: {user_id}")
        return {
            "success": True,
            "message": "Email verified successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )

@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(
    request: Request,
    email: EmailStr,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    Resend email verification link
    
    - Validates user exists and not verified
    - Generates new token
    - Sends email
    """
    try:
        # Check rate limit
        await check_rate_limit(f"resend_verification:{email}", limit=3, window=600)
        
        # Get user
        result = db.table('users').select('*').eq('email', email).execute()
        if not result.data:
            # Don't reveal if email exists
            return {
                "success": True,
                "message": "If the email exists, a verification link will be sent"
            }
        
        user = result.data[0]
        
        # Check if already verified
        if user.get('email_verified', False):
            return {
                "success": True,
                "message": "Email already verified"
            }
        
        # Generate new token
        verification_token = generate_verification_token(user['id'], email)
        
        # Store token in database
        db.table('email_verifications').insert({
            'user_id': user['id'],
            'token': verification_token,
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        # Send email in background
        background_tasks.add_task(
            send_verification_email,
            email,
            f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            verification_token
        )
        
        logger.info(f"Verification email resent to: {email}")
        return {
            "success": True,
            "message": "Verification email sent successfully"
        }
        
    except Exception as e:
        logger.error(f"Resend verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )

@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    Initiate password reset process
    
    - Validates user exists
    - Generates reset token
    - Sends reset email
    """
    try:
        # Check rate limit
        await check_rate_limit(f"forgot_password:{reset_data.email}", limit=3, window=600)
        
        # Get user
        result = db.table('users').select('*').eq('email', reset_data.email).execute()
        if not result.data:
            # Don't reveal if email exists
            return {
                "success": True,
                "message": "If the email exists, a password reset link will be sent"
            }
        
        user = result.data[0]
        
        # Generate reset token
        reset_token = generate_password_reset_token(user['id'], reset_data.email)
        
        # Store token in database
        db.table('password_reset_tokens').insert({
            'user_id': user['id'],
            'token': reset_token,
            'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        # Send email in background
        background_tasks.add_task(
            send_password_reset_email,
            reset_data.email,
            f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            reset_token
        )
        
        # Create audit log
        await create_audit_log(
            db,
            user['id'],
            'password_reset_requested',
            {
                'email': reset_data.email,
                'ip': request.client.host if request.client else None
            },
            request.client.host if request.client else None,
            request.headers.get('user-agent')
        )
        
        logger.info(f"Password reset requested for: {reset_data.email}")
        return {
            "success": True,
            "message": "If the email exists, a password reset link will be sent"
        }
        
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )

@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    reset_data: PasswordResetConfirm,
    db=Depends(get_db)
):
    """
    Reset password using token
    
    - Validates reset token
    - Updates password
    - Revokes all refresh tokens
    - Creates audit log
    """
    try:
        # Decode token
        payload = decode_token(reset_data.token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        if payload.get('type') != 'password_reset':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        # Check token in database
        token_result = db.table('password_reset_tokens') \
            .select('*') \
            .eq('token', reset_data.token) \
            .execute()
        
        if not token_result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token not found"
            )
        
        token_record = token_result.data[0]
        
        # Check if token expired
        if datetime.fromisoformat(token_record['expires_at']) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token expired"
            )
        
        # Get user
        user_id = payload.get('sub')
        user_result = db.table('users').select('*').eq('id', user_id).execute()
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        hashed_password = get_password_hash(reset_data.new_password)
        db.table('users').update({
            'password_hash': hashed_password,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()
        
        # Mark token as used
        db.table('password_reset_tokens').update({
            'used_at': datetime.utcnow().isoformat()
        }).eq('id', token_record['id']).execute()
        
        # Revoke all refresh tokens for security
        db.table('refresh_tokens').update({
            'is_revoked': True,
            'revoked_at': datetime.utcnow().isoformat(),
            'revoked_reason': 'Password reset'
        }).eq('user_id', user_id).execute()
        
        # Create audit log
        await create_audit_log(
            db,
            user_id,
            'password_reset_completed',
            {
                'ip': request.client.host if request.client else None
            },
            request.client.host if request.client else None,
            request.headers.get('user-agent')
        )
        
        logger.info(f"Password reset completed for user: {user_id}")
        return {
            "success": True,
            "message": "Password reset successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

@router.post("/change-password")
async def change_password(
    request: Request,
    change_data: ChangePasswordRequest,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """
    Change password for authenticated user
    
    - Validates current password
    - Updates to new password
    - Revokes all refresh tokens
    - Creates audit log
    """
    try:
        user_id = request.state.user_id
        
        # Get user
        result = db.table('users').select('*').eq('id', user_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = result.data[0]
        
        # Verify current password
        if not verify_password(change_data.current_password, user.get('password_hash')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        hashed_password = get_password_hash(change_data.new_password)
        db.table('users').update({
            'password_hash': hashed_password,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()
        
        # Revoke all refresh tokens for security
        db.table('refresh_tokens').update({
            'is_revoked': True,
            'revoked_at': datetime.utcnow().isoformat(),
            'revoked_reason': 'Password changed'
        }).eq('user_id', user_id).execute()
        
        # Create audit log
        await create_audit_log(
            db,
            user_id,
            'password_changed',
            {
                'ip': request.client.host if request.client else None
            },
            request.client.host if request.client else None,
            request.headers.get('user-agent')
        )
        
        logger.info(f"Password changed for user: {user_id}")
        return {
            "success": True,
            "message": "Password changed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

# ============================================
# SESSION MANAGEMENT
# ============================================

@router.get("/sessions")
async def get_active_sessions(
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """
    Get all active sessions for the user
    
    - Returns all active refresh tokens
    - Includes device information
    """
    try:
        user_id = request.state.user_id
        
        result = db.table('refresh_tokens') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('is_revoked', False) \
            .gt('expires_at', datetime.utcnow().isoformat()) \
            .order('created_at', desc=True) \
            .execute()
        
        sessions = []
        for token in result.data:
            sessions.append({
                'id': token['id'],
                'device_id': token.get('device_id'),
                'device_name': token.get('device_name'),
                'ip_address': token.get('ip_address'),
                'user_agent': token.get('user_agent'),
                'created_at': token.get('created_at'),
                'expires_at': token.get('expires_at')
            })
        
        return {
            "success": True,
            "sessions": sessions,
            "total": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Get sessions error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sessions"
        )

@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """
    Revoke a specific session
    
    - Revokes a specific refresh token
    - Only token owner can revoke
    """
    try:
        user_id = request.state.user_id
        
        # Check session exists and belongs to user
        result = db.table('refresh_tokens') \
            .select('*') \
            .eq('id', session_id) \
            .eq('user_id', user_id) \
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Revoke session
        db.table('refresh_tokens').update({
            'is_revoked': True,
            'revoked_at': datetime.utcnow().isoformat(),
            'revoked_reason': 'User requested'
        }).eq('id', session_id).execute()
        
        # Create audit log
        await create_audit_log(
            db,
            user_id,
            'session_revoked',
            {
                'session_id': session_id,
                'ip': request.client.host if request.client else None
            },
            request.client.host if request.client else None,
            request.headers.get('user-agent')
        )
        
        logger.info(f"Session revoked: {session_id} for user: {user_id}")
        return {
            "success": True,
            "message": "Session revoked successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Revoke session error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session"
        )

# ============================================
# USER INFO & VERIFICATION
# ============================================

@router.get("/me")
async def get_current_user(
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """
    Get current user information
    
    - Returns full user profile
    - Includes role and permissions
    """
    try:
        user_id = request.state.user_id
        
        result = db.table('users').select('*').eq('id', user_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = result.data[0]
        
        # Get user permissions based on role
        role = user.get('role', 'user')
        permissions = ROLE_PERMISSIONS.get(role, [])
        
        return {
            "success": True,
            "user": {
                "id": user['id'],
                "email": user['email'],
                "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                "first_name": user.get('first_name'),
                "last_name": user.get('last_name'),
                "role": role,
                "email_verified": user.get('email_verified', False),
                "phone_number": user.get('phone_number'),
                "is_active": user.get('is_active', True),
                "permissions": permissions,
                "last_login": user.get('last_login')
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )

@router.get("/verify-token")
async def verify_token(
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """
    Verify if the current token is valid
    
    - Returns token validity and user info
    """
    try:
        user_id = request.state.user_id
        
        # Check if user still exists and is active
        result = db.table('users').select('*').eq('id', user_id).execute()
        if not result.data:
            return {"valid": False, "message": "User not found"}
        
        user = result.data[0]
        if not user.get('is_active', True):
            return {"valid": False, "message": "User is deactivated"}
        
        return {
            "valid": True,
            "user": {
                "id": user['id'],
                "email": user['email'],
                "role": user.get('role', 'user')
            }
        }
        
    except HTTPException:
        return {"valid": False, "message": "Invalid token"}
    except Exception as e:
        logger.error(f"Verify token error: {str(e)}")
        return {"valid": False, "message": "Verification failed"}
