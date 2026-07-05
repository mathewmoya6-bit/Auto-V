# app/api/v1/endpoints/vehicles.py
# =============================================================================
# AUTO-V API - Vehicle variants (rates + components + 5yr costs live here)
#
# NOTE: the frontend computes trip totals itself (rate * distance) from the
# fields this endpoint returns, so there is no /calculate endpoint. This
# router only ever needs to hand back rows as stored.
# =============================================================================

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.mileage import VehicleVariant
from app.schemas.mileage import VariantOut

router = APIRouter()


@router.get("/vehicles", response_model=List[VariantOut])
async def list_vehicles(
    category_id: Optional[UUID] = Query(
        None, description="Filter to variants under this vehicle_categories.id"
    ),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(VehicleVariant).where(VehicleVariant.is_active.is_(True))
    if category_id is not None:
        stmt = stmt.where(VehicleVariant.category_id == category_id)
    stmt = stmt.order_by(VehicleVariant.label)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/vehicles/{vehicle_id}", response_model=VariantOut)
async def get_vehicle(vehicle_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(VehicleVariant).where(
        VehicleVariant.id == vehicle_id,
        VehicleVariant.is_active.is_(True),
    )
    result = await db.execute(stmt)
    variant = result.scalar_one_or_none()

    if variant is None:
        raise HTTPException(status_code=404, detail="Vehicle variant not found")

    return variant
