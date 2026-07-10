# app/api/v1/routes/vehicles.py
# =============================================================================
# AUTO-V API - Vehicle Routes
# =============================================================================
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.schemas.user import UserProfile
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def get_vehicle_service() -> VehicleService:
    return VehicleService()


# =============================================================================
# PUBLIC REFERENCE DATA — no auth required.
#
# IMPORTANT: this must be declared BEFORE the /{vehicle_id} route below.
# FastAPI/Starlette matches routes in registration order, and "/models" would
# otherwise be swallowed by "/{vehicle_id}" (treating "models" as a UUID),
# which is exactly what was causing the 401 — it was hitting the
# authenticated single-vehicle lookup instead of a real "list models" route.
# =============================================================================

class VehicleModelEntry(BaseModel):
    make: str
    model: str


# Static reference list for now. Swap the body of list_vehicle_models() for a
# Supabase table lookup (e.g. a `vehicle_makes` / `vehicle_models` table) once
# one exists — the response shape here is designed to match that migration
# path with no frontend changes needed.
_VEHICLE_MODEL_CATALOG: List[VehicleModelEntry] = [
    VehicleModelEntry(make="Toyota", model="Corolla"),
    VehicleModelEntry(make="Toyota", model="Axio"),
    VehicleModelEntry(make="Toyota", model="Camry"),
    VehicleModelEntry(make="Toyota", model="RAV4"),
    VehicleModelEntry(make="Toyota", model="Hilux"),
    VehicleModelEntry(make="Toyota", model="Land Cruiser"),
    VehicleModelEntry(make="Honda", model="Civic"),
    VehicleModelEntry(make="Honda", model="Accord"),
    VehicleModelEntry(make="Honda", model="CR-V"),
    VehicleModelEntry(make="Honda", model="Fit"),
    VehicleModelEntry(make="Nissan", model="X-Trail"),
    VehicleModelEntry(make="Nissan", model="Patrol"),
    VehicleModelEntry(make="Nissan", model="Note"),
    VehicleModelEntry(make="Nissan", model="Qashqai"),
    VehicleModelEntry(make="BMW", model="X5"),
    VehicleModelEntry(make="BMW", model="3 Series"),
    VehicleModelEntry(make="BMW", model="5 Series"),
    VehicleModelEntry(make="BMW", model="7 Series"),
    VehicleModelEntry(make="Mercedes", model="C-Class"),
    VehicleModelEntry(make="Mercedes", model="E-Class"),
    VehicleModelEntry(make="Mercedes", model="GLC"),
    VehicleModelEntry(make="Mercedes", model="GLE"),
]


@router.get("/models", response_model=List[VehicleModelEntry])
async def list_vehicle_models():
    """
    Public catalog of make/model combinations, used to populate dropdowns
    (e.g. instant-value.html). Deliberately has NO auth dependency — this
    is reference data, not user data.
    """
    return _VEHICLE_MODEL_CATALOG


# =============================================================================
# AUTHENTICATED USER-VEHICLE CRUD (unchanged from before)
# =============================================================================

@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreate,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    return await service.create_vehicle(UUID(current_user.id), payload)


@router.get("/", response_model=List[VehicleResponse])
async def list_vehicles(
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    return await service.list_vehicles(UUID(current_user.id))


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    is_admin = current_user.role == "admin"
    return await service.get_vehicle(vehicle_id, UUID(current_user.id), is_admin)


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdate,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    is_admin = current_user.role == "admin"
    return await service.update_vehicle(vehicle_id, UUID(current_user.id), payload, is_admin)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    is_admin = current_user.role == "admin"
    await service.delete_vehicle(vehicle_id, UUID(current_user.id), is_admin)
