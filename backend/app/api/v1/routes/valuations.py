# app/api/v1/routes/valuations.py
# =============================================================================
# AUTO-V API - Valuation Routes
# =============================================================================
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status, HTTPException, Query

from app.core.security import get_current_user, get_current_admin_user
from app.schemas.user import UserProfile
from app.schemas.valuations import (
    ValuationRequest,
    ValuationResponse,
    ValuationUpdate,
    ValuationStats,
    ValuationHistoryResponse
)
from app.services.valuation_service import ValuationService

router = APIRouter(tags=["Valuations"])


def get_valuation_service() -> ValuationService:
    return ValuationService()


# ─── Valuation CRUD ──────────────────────────────────────────────────

@router.post("/", response_model=ValuationResponse, status_code=status.HTTP_201_CREATED)
async def create_valuation(
    payload: ValuationRequest,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Create a new valuation.
    Runs the valuation and persists it to the valuations table.
    """
    return await service.create_valuation(UUID(current_user.id), payload)


@router.get("/", response_model=List[ValuationResponse])
async def list_valuations(
    current_user: UserProfile = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Get all valuations for the current user.
    Supports pagination with limit and offset.
    """
    return await service.list_valuations(UUID(current_user.id), limit, offset)


@router.get("/history", response_model=List[ValuationHistoryResponse])
async def get_valuation_history(
    current_user: UserProfile = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Get valuation history for the current user.
    Returns the most recent valuations.
    """
    return await service.get_valuation_history(UUID(current_user.id), limit)


@router.get("/stats", response_model=ValuationStats)
async def get_valuation_stats(
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Get statistics about user's valuations.
    Includes total count, average value, confidence scores, etc.
    """
    return await service.get_valuation_stats(UUID(current_user.id))


@router.get("/{valuation_id}", response_model=ValuationResponse)
async def get_valuation(
    valuation_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Get a specific valuation by ID.
    Only the owner or admin can access it.
    """
    is_admin = current_user.role == "admin"
    return await service.get_valuation(valuation_id, UUID(current_user.id), is_admin)


@router.put("/{valuation_id}", response_model=ValuationResponse)
async def update_valuation(
    valuation_id: UUID,
    payload: ValuationUpdate,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Update a valuation.
    Only the owner or admin can update it.
    """
    is_admin = current_user.role == "admin"
    return await service.update_valuation(valuation_id, UUID(current_user.id), payload, is_admin)


@router.delete("/{valuation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_valuation(
    valuation_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Delete a valuation.
    Only the owner or admin can delete it.
    """
    is_admin = current_user.role == "admin"
    await service.delete_valuation(valuation_id, UUID(current_user.id), is_admin)


# ─── Instant Valuation ──────────────────────────────────────────────

@router.post("/instant", response_model=ValuationResponse)
async def instant_valuation(
    payload: ValuationRequest,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Get an instant valuation without persisting to database.
    Same calculation as regular valuation but not saved.
    Useful for quick previews before committing.
    """
    return await service.instant_valuation(UUID(current_user.id), payload)


@router.post("/instant/save", response_model=ValuationResponse, status_code=status.HTTP_201_CREATED)
async def instant_valuation_save(
    payload: ValuationRequest,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Get instant valuation AND save it to the database.
    Combines the instant calculation with persistence.
    """
    return await service.instant_valuation_save(UUID(current_user.id), payload)


# ─── Vehicle Valuations ─────────────────────────────────────────────

@router.get("/vehicles/{vehicle_id}/valuation", response_model=ValuationResponse)
async def get_vehicle_valuation(
    vehicle_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Get the latest valuation for a specific vehicle.
    """
    return await service.get_vehicle_valuation(vehicle_id, UUID(current_user.id))


@router.get("/vehicles/{vehicle_id}/history", response_model=List[ValuationHistoryResponse])
async def get_vehicle_valuation_history(
    vehicle_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Get valuation history for a specific vehicle.
    """
    return await service.get_vehicle_valuation_history(vehicle_id, UUID(current_user.id), limit)


# ─── Admin Endpoints ──────────────────────────────────────────────

@router.get("/admin/all", response_model=List[ValuationResponse])
async def admin_list_all_valuations(
    current_admin: UserProfile = Depends(get_current_admin_user),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    List all valuations across all users (Admin only).
    """
    return await service.admin_list_all_valuations(limit, offset)


@router.get("/admin/stats", response_model=dict)
async def admin_get_valuation_stats(
    current_admin: UserProfile = Depends(get_current_admin_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Get global valuation statistics (Admin only).
    """
    return await service.admin_get_valuation_stats()


# ─── Export / Download ──────────────────────────────────────────────

@router.get("/{valuation_id}/certificate")
async def get_valuation_certificate(
    valuation_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Generate and download a valuation certificate.
    Returns a PDF certificate for the valuation.
    """
    is_admin = current_user.role == "admin"
    return await service.generate_certificate(valuation_id, UUID(current_user.id), is_admin)


@router.get("/export/csv")
async def export_valuations_csv(
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """
    Export user's valuations to CSV format.
    """
    return await service.export_valuations_csv(UUID(current_user.id))
