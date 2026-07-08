# app/api/v1/routes/vehicles.py
# =============================================================================
# AUTO-V API - Vehicle Routes
# =============================================================================
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.security import get_current_user
from app.schemas.user import UserProfile
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def get_vehicle_service() -> VehicleService:
    return VehicleService()


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
