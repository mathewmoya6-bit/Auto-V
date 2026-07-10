from fastapi import APIRouter, HTTPException, Depends
from app.core.database import supabase
from app.schemas.auth import UserLogin, UserRegister, TokenResponse
from app.core.security import get_current_user

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
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


@router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register new user"""
    try:
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name
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


@router.post("/auth/logout")
async def logout(current_user = Depends(get_current_user)):
    """Logout current user"""
    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user info"""
    return current_user
