from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.mileage import (
    VehicleCategoryResponse,
    VehicleVariantResponse,
)
from app.models.mileage import VehicleCategory, VehicleVariant

router = APIRouter()


@router.get("/categories", response_model=List[VehicleCategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    """
    Get all vehicle categories.
    """
    return db.query(VehicleCategory).all()


@router.get("/variants", response_model=List[VehicleVariantResponse])
async def get_variants(db: Session = Depends(get_db)):
    """
    Get all vehicle variants.
    """
    return db.query(VehicleVariant).all()
