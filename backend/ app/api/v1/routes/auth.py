# app/api/v1/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import uuid

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    verify_password, get_password_hash, validate_password_strength,
    JWTBearer
)
from app.core.logging import get_logger
from app.models.user import UserCreate, UserLogin, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db=Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user exists
        existing_user = db.table('users').select('*').eq('email', user_data.email).execute()
        if existing_user.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate password strength
        if not validate_password_strength(user_data.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet strength requirements"
            )
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user
        user_id = str(uuid.uuid4())
        new_user = {
            'id': user_id,
            'email': user_data.email,
            'password_hash': hashed_password,
            'first_name': user_data.first_name,
            'last_name': user_data.last_name,
            'phone_number': user_data.phone_number,
            'role': 'user',
            'email_verified': False,
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
            'preferences': {}
        }
        db.table('user_profiles').insert(profile).execute()
        
        logger.info(f"User registered successfully: {user_data.email}")
        
        return UserResponse(
            id=user_id,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role='user',
            email_verified=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db=Depends(get_db)):
    """Login user and return tokens"""
    try:
        # Find user by email
        result = db.table('users').select('*').eq('email', user_data.email).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = result.data[0]
        
        # Verify password
        if not verify_password(user_data.password, user.get('password_hash')):
            # Log failed attempt
            logger.warning(f"Failed login attempt for email: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create tokens
        token_data = {
            "sub": user['id'],
            "email": user['email'],
            "role": user.get('role', 'user')
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Update last login
        db.table('users').update({
            'last_login': datetime.utcnow().isoformat()
        }).eq('id', user['id']).execute()
        
        logger.info(f"User logged in successfully: {user_data.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, db=Depends(get_db)):
    """Refresh access token using refresh token"""
    try:
        # Get refresh token from request body
        body = await request.json()
        refresh_token = body.get('refresh_token')
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )
        
        # Decode refresh token
        payload = decode_token(refresh_token)
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
        
        # Get user
        user_id = payload.get('sub')
        result = db.table('users').select('*').eq('id', user_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        user = result.data[0]
        
        # Create new tokens
        token_data = {
            "sub": user['id'],
            "email": user['email'],
            "role": user.get('role', 'user')
        }
        
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        logger.info(f"Tokens refreshed for user: {user['email']}")
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout(request: Request, token_data: dict = Depends(JWTBearer())):
    """Logout user (client-side token invalidation)"""
    # This is a client-side logout - token remains valid until expiry
    # For server-side invalidation, implement token blacklist in Redis
    logger.info(f"User logged out: {request.state.user_email}")
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user(request: Request, token_data: dict = Depends(JWTBearer()), db=Depends(get_db)):
    """Get current user information"""
    try:
        user_id = request.state.user_id
        result = db.table('users').select('*').eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = result.data[0]
        
        return UserResponse(
            id=user['id'],
            email=user['email'],
            first_name=user.get('first_name'),
            last_name=user.get('last_name'),
            role=user.get('role', 'user'),
            email_verified=user.get('email_verified', False)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )

@router.post("/forgot-password")
async def forgot_password(email: str, db=Depends(get_db)):
    """Send password reset email"""
    try:
        # Check if user exists
        result = db.table('users').select('*').eq('email', email).execute()
        if not result.data:
            # Don't reveal if email exists or not
            return {"message": "If the email exists, a reset link will be sent"}
        
        # Generate reset token
        reset_token = create_access_token(
            {"sub": result.data[0]['id'], "purpose": "password_reset"},
            timedelta(hours=1)
        )
        
        # Store reset token in database
        db.table('password_reset_tokens').insert({
            'user_id': result.data[0]['id'],
            'token': reset_token,
            'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }).execute()
        
        # Send email with reset link
        # TODO: Implement email sending
        # await send_reset_email(email, reset_token)
        
        logger.info(f"Password reset requested for: {email}")
        return {"message": "If the email exists, a reset link will be sent"}
        
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset"
        )

@router.post("/reset-password")
async def reset_password(token: str, new_password: str, db=Depends(get_db)):
    """Reset password using token"""
    try:
        # Validate token
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )
        
        # Check if token is for password reset
        if payload.get('purpose') != 'password_reset':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token purpose"
            )
        
        # Get user
        user_id = payload.get('sub')
        result = db.table('users').select('*').eq('id', user_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate new password strength
        if not validate_password_strength(new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet strength requirements"
            )
        
        # Update password
        hashed_password = get_password_hash(new_password)
        db.table('users').update({
            'password_hash': hashed_password,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()
        
        # Delete used reset token
        db.table('password_reset_tokens').delete().eq('token', token).execute()
        
        logger.info(f"Password reset successful for user: {user_id}")
        return {"message": "Password reset successful"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )
