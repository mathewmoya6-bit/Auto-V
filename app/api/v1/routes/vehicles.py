# app/api/v1/routes/vehicles.py
# =============================================================================
# AUTO-V API - Vehicle & VIN Routes
# =============================================================================

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.vehicle import Vehicle, VINScan
from app.api.v1.routes.auth import get_current_user
from app.models.user import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


class VehicleCreateRequest(BaseModel):
    vin: str
    registration_number: Optional[str] = None
    make: str
    model: str
    year: int
    vehicle_type: Optional[str] = "Car"
    odometer: Optional[int] = None
    condition: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    existing = await db.execute(select(Vehicle).where(Vehicle.vin == payload.vin))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A vehicle with this VIN already exists")

    vehicle = Vehicle(user_id=current_user.id, **payload.model_dump())
    db.add(vehicle)
    try:
        await db.commit()
        await db.refresh(vehicle)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create vehicle: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create vehicle")

    return vehicle.to_dict()


@router.get("")
async def list_my_vehicles(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    result = await db.execute(
        select(Vehicle).where(Vehicle.user_id == current_user.id).order_by(Vehicle.created_at.desc())
    )
    return [v.to_dict() for v in result.scalars().all()]


@router.get("/{vehicle_id}")
async def get_vehicle(vehicle_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle.to_dict()


@router.get("/vin/{vin}")
async def get_vehicle_by_vin(vin: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vehicle).where(Vehicle.vin == vin))
    vehicle = result.scalar_one_or_none()
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No vehicle found for this VIN")
    return vehicle.to_dict()


@router.get("/vin-scans/history")
async def list_vin_scans(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    result = await db.execute(
        select(VINScan).where(VINScan.user_id == current_user.id).order_by(VINScan.created_at.desc())
    )
    return [s.to_dict() for s in result.scalars().all()]
