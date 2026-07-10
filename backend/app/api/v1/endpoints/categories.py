from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.core.database import supabase, admin
from app.schemas.mileage import VehicleCategoryCreate, VehicleCategoryResponse
from app.core.security import get_current_user

router = APIRouter()


@router.get("/categories", response_model=List[VehicleCategoryResponse])
async def get_categories():
    """Get all vehicle categories"""
    try:
        result = (
            supabase
            .table("vehicle_categories")
            .select("*")
            .order("name")
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categories", response_model=VehicleCategoryResponse)
async def create_category(
    category: VehicleCategoryCreate,
    current_user = Depends(get_current_user)
):
    """Create a new vehicle category (admin only)"""
    try:
        result = (
            admin
            .table("vehicle_categories")
            .insert(category.model_dump())
            .execute()
        )
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/categories/{category_id}", response_model=VehicleCategoryResponse)
async def update_category(
    category_id: int,
    category: VehicleCategoryCreate,
    current_user = Depends(get_current_user)
):
    """Update an existing category (admin only)"""
    try:
        result = (
            admin
            .table("vehicle_categories")
            .update(category.model_dump())
            .eq("id", category_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Category not found")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    current_user = Depends(get_current_user)
):
    """Delete a category (admin only)"""
    try:
        result = (
            admin
            .table("vehicle_categories")
            .delete()
            .eq("id", category_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Category not found")
        return {"message": "Category deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
