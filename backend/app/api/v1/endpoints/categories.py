# app/api/v1/endpoints/categories.py
# =============================================================================
# AUTO-V API - Vehicle categories (fuel_type lives here, NOT on variants)
# =============================================================================

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.mileage import VehicleCategory
from app.schemas.mileage import CategoryOut

router = APIRouter()


@router.get("/categories", response_model=List[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """All active vehicle categories, alphabetical."""
    stmt = (
        select(VehicleCategory)
        .where(VehicleCategory.is_active.is_(True))
        .order_by(VehicleCategory.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
