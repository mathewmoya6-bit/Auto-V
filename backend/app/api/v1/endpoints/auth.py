# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, HTTPException, Depends
from app.core.database import supabase
from app.schemas.auth import (
    UserLogin, 
    UserRegister, 
    TokenResponse, 
    RefreshRequest,
    RefreshResponse,
    UserResponse
)
from app.core.security import get_current_user

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Login user with email and password"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        
        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user=response.user.model_dump()
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register new user"""
    try:
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name,
                    "phone_number": user_data.phone_number
                }
            }
        })
        
        if not response.user:
            raise HTTPException(status_code=400, detail="Registration failed")
            
        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user=response.user.model_dump()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh access token using refresh token"""
    try:
        response = supabase.auth.refresh_session(request.refresh_token)
        return RefreshResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer"
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(current_user = Depends(get_current_user)):
    """Logout current user"""
    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.user_metadata.get("full_name") if current_user.user_metadata else None,
        phone_number=current_user.user_metadata.get("phone_number") if current_user.user_metadata else None,
        created_at=current_user.created_at,
        is_active=True,
        is_admin=False
    )
