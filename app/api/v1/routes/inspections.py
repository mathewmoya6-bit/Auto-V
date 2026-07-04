# app/api/v1/routes/inspections.py
# =============================================================================
# AUTO-V API - Inspection Routes
# =============================================================================

import logging
from datetime import date as date_type
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.inspection import Inspection
from app.models.vehicle import Vehicle
from app.api.v1.routes.auth import get_current_user
from app.models.user import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inspections", tags=["Inspection"])


class InspectionCreateRequest(BaseModel):
    vehicle_id: str
    inspection_type: Optional[str] = "Standard"
    inspection_date: date_type
    inspection_location: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_inspection(
    payload: InspectionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    vehicle_result = await db.execute(select(Vehicle).where(Vehicle.id == payload.vehicle_id))
    if vehicle_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    inspection = Inspection(
        vehicle_id=payload.vehicle_id,
        inspector_id=current_user.id,
        inspection_type=payload.inspection_type,
        inspection_date=payload.inspection_date,
        inspection_location=payload.inspection_location,
        status="pending",
    )
    db.add(inspection)
    try:
        await db.commit()
        await db.refresh(inspection)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create inspection: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create inspection")

    return inspection.to_dict()


@router.get("")
async def list_inspections(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    result = await db.execute(
        select(Inspection)
        .where(Inspection.inspector_id == current_user.id)
        .order_by(Inspection.created_at.desc())
    )
    return [i.to_dict() for i in result.scalars().all()]


@router.get("/{inspection_id}")
async def get_inspection(inspection_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return inspection.to_dict()
