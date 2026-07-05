# backend/app/api/v1/endpoints/auth.py
# =============================================================================
# Authentication Endpoints - Login, Register, Logout, Me
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import bcrypt
import jwt
from datetime import datetime, timedelta
import uuid
import logging

from app.core.database import get_db
from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# =============================================================================
# Pydantic Models
# =============================================================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    company: Optional[str] = None
    role: str = "user"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: str
    member_id: Optional[str] = None
    is_first_login: bool
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None

# =============================================================================
# Helper Functions
# =============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Get the current authenticated user."""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# =============================================================================
# Endpoints
# =============================================================================

@router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    """
    try:
        # Check if user already exists
        query = select(User).where(User.email == user_data.email)
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please login."
            )
        
        # Generate member ID
        member_id = f"AUTO-V-{str(uuid.uuid4())[:8].upper()}"
        
        # Create new user
        new_user = User(
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name,
            phone=user_data.phone,
            company=user_data.company,
            role=user_data.role or "user",
            member_id=member_id,
            is_first_login=True,
            is_active=True
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"✅ New user registered: {new_user.email}")
        
        # Create access token
        token_data = {
            "sub": str(new_user.id),
            "email": new_user.email,
            "role": new_user.role
        }
        access_token = create_access_token(token_data)
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=str(new_user.id),
                email=new_user.email,
                full_name=new_user.full_name,
                phone=new_user.phone,
                company=new_user.company,
                role=new_user.role,
                member_id=new_user.member_id,
                is_first_login=new_user.is_first_login,
                created_at=new_user.created_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Login a user and return an access token.
    """
    try:
        # Find user by email
        query = select(User).where(User.email == login_data.email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Verify password
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        # Create access token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        }
        access_token = create_access_token(token_data)
        
        logger.info(f"✅ User logged in: {user.email}")
        
        # If first login, set flag
        if user.is_first_login:
            user.is_first_login = False
            await db.commit()
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                phone=user.phone,
                company=user.company,
                role=user.role,
                member_id=user.member_id,
                is_first_login=user.is_first_login,
                created_at=user.created_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        company=current_user.company,
        role=current_user.role,
        member_id=current_user.member_id,
        is_first_login=current_user.is_first_login,
        created_at=current_user.created_at
    )


@router.post("/auth/logout")
async def logout():
    """
    Logout endpoint - client side should remove the token.
    """
    return {"message": "Logout successful"}


@router.post("/auth/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password.
    """
    try:
        # Verify current password
        if not verify_password(request.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        current_user.password_hash = hash_password(request.new_password)
        await db.commit()
        
        logger.info(f"✅ Password changed for user: {current_user.email}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(e)}"
        )


@router.post("/auth/reset-password")
async def reset_password(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request a password reset.
    """
    try:
        # Find user
        query = select(User).where(User.email == request.email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            # Don't reveal that the user doesn't exist for security
            return {"message": "If your email is registered, you will receive a reset link"}
        
        # In production, send an email with reset link
        logger.info(f"Password reset requested for: {request.email}")
        
        return {"message": "Password reset instructions sent to your email"}
        
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset"
        )


@router.put("/auth/profile")
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user profile.
    """
    try:
        if request.full_name:
            current_user.full_name = request.full_name
        if request.phone:
            current_user.phone = request.phone
        if request.company:
            current_user.company = request.company
        
        await db.commit()
        
        logger.info(f"✅ Profile updated for user: {current_user.email}")
        
        return {
            "message": "Profile updated successfully",
            "user": UserResponse(
                id=str(current_user.id),
                email=current_user.email,
                full_name=current_user.full_name,
                phone=current_user.phone,
                company=current_user.company,
                role=current_user.role,
                member_id=current_user.member_id,
                is_first_login=current_user.is_first_login,
                created_at=current_user.created_at
            )
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Update profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )
