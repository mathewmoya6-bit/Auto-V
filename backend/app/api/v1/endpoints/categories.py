from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas import CategoryOut, VariantOut

router = APIRouter()

@router.get("/categories", response_model=List[CategoryOut])
async def get_categories():
    """
    Get all vehicle categories
    """
    # Your logic here
    return []

@router.get("/variants", response_model=List[VariantOut])
async def get_variants():
    """
    Get all vehicle variants
    """
    # Your logic here
    return []
