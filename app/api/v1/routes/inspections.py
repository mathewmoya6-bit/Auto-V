# app/api/v1/routes/inspections.py
# =============================================================================
# AUTO-V API - Inspection Routes
# =============================================================================
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.security import get_current_admin_user, get_current_user
from app.schemas.inspection import (
    InspectionComplete,
    InspectionCreate,
    InspectionResponse,
    InspectionUpdate,
)
from app.schemas.user import UserProfile
from app.services.inspection_service import InspectionService

router = APIRouter(prefix="/inspections", tags=["inspections"])


def get_inspection_service() -> InspectionService:
    return InspectionService()


@router.post("/", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
async def create_inspection(
    payload: InspectionCreate,
    current_user: UserProfile = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
):
    return await service.create_inspection(UUID(current_user.id), payload)


@router.get("/", response_model=List[InspectionResponse])
async def list_inspections(
    current_user: UserProfile = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
):
    return await service.list_inspections(UUID(current_user.id))


@router.get("/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(
    inspection_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
):
    is_admin = current_user.role == "admin"
    return await service.get_inspection(inspection_id, UUID(current_user.id), is_admin)


@router.patch("/{inspection_id}", response_model=InspectionResponse)
async def update_inspection(
    inspection_id: UUID,
    payload: InspectionUpdate,
    current_user: UserProfile = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
):
    is_admin = current_user.role == "admin"
    return await service.update_inspection(inspection_id, UUID(current_user.id), payload, is_admin)


@router.post("/{inspection_id}/complete", response_model=InspectionResponse)
async def complete_inspection(
    inspection_id: UUID,
    payload: InspectionComplete,
    current_admin: UserProfile = Depends(get_current_admin_user),
    service: InspectionService = Depends(get_inspection_service),
):
    """Inspector/admin submits final checklist results."""
    return await service.complete_inspection(inspection_id, UUID(current_admin.id), payload)


@router.delete("/{inspection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inspection(
    inspection_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: InspectionService = Depends(get_inspection_service),
):
    is_admin = current_user.role == "admin"
    await service.delete_inspection(inspection_id, UUID(current_user.id), is_admin)
