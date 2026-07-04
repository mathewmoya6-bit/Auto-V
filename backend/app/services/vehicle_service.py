# app/api/v1/routes/vehicles.py

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models import UserProfile, Vehicle

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


# ─── Schemas ────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    vin: str = Field(..., min_length=17, max_length=17)
    registration_number: Optional[str] = None
    make: str
    model: str
    year: int
    vehicle_type: Optional[str] = "Car"
    body_type: Optional[str] = None
    engine_cc: Optional[int] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    odometer: Optional[int] = None
    color: Optional[str] = None
    condition: Optional[str] = None
    accident_history: Optional[str] = "None"


class VehicleUpdate(BaseModel):
    registration_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    body_type: Optional[str] = None
    engine_cc: Optional[int] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    odometer: Optional[int] = None
    color: Optional[str] = None
    condition: Optional[str] = None
    accident_history: Optional[str] = None


# ─── Helpers ────────────────────────────────────────────────────

async def _get_owned_vehicle(vehicle_id: str, user: UserProfile, db: AsyncSession) -> Vehicle:
    try:
        vid = uuid.UUID(vehicle_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle id")

    result = await db.execute(select(Vehicle).where(Vehicle.id == vid))
    vehicle = result.scalar_one_or_none()

    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    if vehicle.user_id != user.id and user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your vehicle")

    return vehicle


# ─── Routes ─────────────────────────────────────────────────────

@router.get("")
async def list_my_vehicles(
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Vehicle)
        .where(Vehicle.user_id == current_user.id, Vehicle.is_deleted == False)  # noqa: E712
        .order_by(Vehicle.created_at.desc())
    )
    vehicles = result.scalars().all()
    return [v.to_dict() for v in vehicles]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    body: VehicleCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Vehicle).where(Vehicle.vin == body.vin))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A vehicle with this VIN already exists")

    vehicle = Vehicle(user_id=current_user.id, **body.model_dump())
    db.add(vehicle)

    current_user.has_vehicle = True

    await db.commit()
    await db.refresh(vehicle)
    return vehicle.to_dict()


@router.get("/{vehicle_id}")
async def get_vehicle(
    vehicle_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vehicle = await _get_owned_vehicle(vehicle_id, current_user, db)
    return vehicle.to_dict()


@router.patch("/{vehicle_id}")
async def update_vehicle(
    vehicle_id: str,
    body: VehicleUpdate,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vehicle = await _get_owned_vehicle(vehicle_id, current_user, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle.to_dict()


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete — matches SoftDeleteMixin on the Vehicle model.
    Doesn't touch VIN/registration uniqueness constraints, so a
    permanently-retired vehicle's VIN can't be re-registered by
    anyone unless you also null those fields out here."""
    vehicle = await _get_owned_vehicle(vehicle_id, current_user, db)
    vehicle.is_deleted = True
    from datetime import datetime
    vehicle.deleted_at = datetime.utcnow()
    await db.commit()
    return None


@router.get("/admin/all")
async def list_all_vehicles(
    _: UserProfile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Vehicle).order_by(Vehicle.created_at.desc()))
    vehicles = result.scalars().all()
    return [v.to_dict() for v in vehicles]
