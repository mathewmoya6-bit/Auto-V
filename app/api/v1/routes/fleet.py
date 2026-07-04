# app/api/v1/routes/fleet.py
# =============================================================================
# AUTO-V API - Fleet Management Routes
# =============================================================================

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.fleet import Fleet, FleetVehicle
from app.models.vehicle import Vehicle
from app.api.v1.routes.auth import get_current_user
from app.models.user import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fleet", tags=["Fleet"])


class FleetCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    fleet_code: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_fleet(
    payload: FleetCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    fleet = Fleet(owner_id=current_user.id, **payload.model_dump())
    db.add(fleet)
    try:
        await db.commit()
        await db.refresh(fleet)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create fleet: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create fleet")

    return fleet.to_dict()


@router.get("")
async def list_my_fleets(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    result = await db.execute(
        select(Fleet).where(Fleet.owner_id == current_user.id).order_by(Fleet.created_at.desc())
    )
    return [f.to_dict() for f in result.scalars().all()]


@router.get("/{fleet_id}")
async def get_fleet(fleet_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fleet).where(Fleet.id == fleet_id))
    fleet = result.scalar_one_or_none()
    if fleet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fleet not found")
    return fleet.to_dict()


class AddVehicleToFleetRequest(BaseModel):
    vehicle_id: str
    fleet_number: Optional[str] = None


@router.post("/{fleet_id}/vehicles", status_code=status.HTTP_201_CREATED)
async def add_vehicle_to_fleet(
    fleet_id: str,
    payload: AddVehicleToFleetRequest,
    db: AsyncSession = Depends(get_db),
):
    fleet_result = await db.execute(select(Fleet).where(Fleet.id == fleet_id))
    if fleet_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fleet not found")

    vehicle_result = await db.execute(select(Vehicle).where(Vehicle.id == payload.vehicle_id))
    if vehicle_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    fv = FleetVehicle(fleet_id=fleet_id, vehicle_id=payload.vehicle_id, fleet_number=payload.fleet_number)
    db.add(fv)
    try:
        await db.commit()
        await db.refresh(fv)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to add vehicle to fleet: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add vehicle to fleet")

    return {"id": str(fv.id), "fleet_id": str(fv.fleet_id), "vehicle_id": str(fv.vehicle_id)}
