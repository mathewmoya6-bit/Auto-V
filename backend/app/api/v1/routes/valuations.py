# app/api/v1/routes/valuations.py
# =============================================================================
# AUTO-V API - Valuation Routes
# =============================================================================

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.valuation import Valuation
from app.models.vehicle import Vehicle
from app.api.v1.routes.auth import get_current_user
from app.models.user import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/valuations", tags=["Valuation"])


class ValuationCreateRequest(BaseModel):
    vehicle_id: str
    valuation_type: Optional[str] = "standard"
    purpose: Optional[str] = None
    region: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_valuation(
    payload: ValuationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    vehicle_result = await db.execute(select(Vehicle).where(Vehicle.id == payload.vehicle_id))
    if vehicle_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    valuation = Valuation(
        vehicle_id=payload.vehicle_id,
        user_id=current_user.id,
        valuation_type=payload.valuation_type,
        purpose=payload.purpose,
        region=payload.region,
        status="draft",
    )
    db.add(valuation)
    try:
        await db.commit()
        await db.refresh(valuation)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create valuation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create valuation")

    return valuation.to_dict()


@router.get("")
async def list_my_valuations(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    result = await db.execute(
        select(Valuation).where(Valuation.user_id == current_user.id).order_by(Valuation.created_at.desc())
    )
    return [v.to_dict() for v in result.scalars().all()]


@router.get("/{valuation_id}")
async def get_valuation(valuation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Valuation).where(Valuation.id == valuation_id))
    valuation = result.scalar_one_or_none()
    if valuation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Valuation not found")
    return valuation.to_dict()
