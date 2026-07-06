from fastapi import APIRouter
from typing import List
from app.schemas.mileage import CategoryOut, VariantOut

router = APIRouter()

@router.get("/categories", response_model=List[CategoryOut])
async def get_categories():
    return []

@router.get("/variants", response_model=List[VariantOut])
async def get_variants():
    return []
