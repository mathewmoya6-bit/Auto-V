from fastapi import APIRouter, HTTPException, Depends

from app.core.database import supabase
from app.core.security import get_current_user

from app.schemas.auth import (
    UserLogin,
    UserRegister,
    TokenResponse,
    RefreshRequest,
    RefreshResponse,
    UserResponse,
)

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Login user"""

    try:
        response = supabase.auth.sign_in_with_password(
            {
                "email": user_data.email,
                "password": user_data.password,
            }
        )

        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
            user=response.user.model_dump(),
        )

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register user"""

    try:
        response = supabase.auth.sign_up(
            {
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "full_name": user_data.full_name,
                        "phone_number": user_data.phone_number,
                    }
                },
            }
        )

        if response.user is None:
            raise HTTPException(
                status_code=400,
                detail="Registration failed",
            )

        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
            user=response.user.model_dump(),
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh JWT token"""

    try:
        response = supabase.auth.refresh_session(request.refresh_token)

        return RefreshResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
        )

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    """Logout current user"""

    try:
        supabase.auth.sign_out()

        return {
            "message": "Logged out successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(get_current_user),
):
    """Current logged-in user"""

    metadata = current_user.user_metadata or {}

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=metadata.get("full_name"),
        phone_number=metadata.get("phone_number"),
        created_at=str(current_user.created_at),
        is_active=True,
        is_verified=getattr(current_user, "email_confirmed_at", None) is not None,
        is_admin=False,
        role=metadata.get("role", "user"),
    )
