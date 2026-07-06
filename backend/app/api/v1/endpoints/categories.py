from fastapi import APIRouter, HTTPException
from typing import List

# Import directly from the specific schema modules
from app.schemas.mileage import CategoryOut, VariantOut

router = APIRouter()

@router.get("/categories", response_model=List[CategoryOut])
async def get_categories():
    """
    Get all vehicle categories
    """
    return []

@router.get("/variants", response_model=List[VariantOut])
async def get_variants():
    """
    Get all vehicle variants
    """
    return []
