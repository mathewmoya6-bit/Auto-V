from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.core.database import supabase, admin
from app.schemas.users import UserResponse, UserUpdate
from app.core.security import get_current_user

router = APIRouter()


@router.get("/users/me", response_model=UserResponse)
async def get_my_profile(current_user = Depends(get_current_user)):
    """Get current user's profile"""
    try:
        result = (
            supabase
            .table("users")
            .select("*")
            .eq("id", current_user.id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user = Depends(get_current_user)
):
    """Update current user's profile"""
    try:
        result = (
            admin
            .table("users")
            .update(user_update.model_dump(exclude_unset=True))
            .eq("id", current_user.id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(current_user = Depends(get_current_user)):
    """Get all users (admin only)"""
    try:
        result = (
            admin
            .table("users")
            .select("*")
            .order("created_at")
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """Get user by ID (admin only)"""
    try:
        result = (
            admin
            .table("users")
            .select("*")
            .eq("id", user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
