# app/api/v1/routes/valuations.py
# =============================================================================
# AUTO-V API - Valuation Routes
# =============================================================================
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.security import get_current_user
from app.schemas.user import UserProfile
from app.schemas.valuation import ValuationRequest, ValuationResponse
from app.services.valuation_service import ValuationService

router = APIRouter(prefix="/valuations", tags=["valuations"])


def get_valuation_service() -> ValuationService:
    return ValuationService()


@router.post("/", response_model=ValuationResponse, status_code=status.HTTP_201_CREATED)
async def create_valuation(
    payload: ValuationRequest,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """Runs the valuation and persists it to the valuations table."""
    return await service.create_valuation(UUID(current_user.id), payload)


@router.post("/instant", response_model=ValuationResponse)
async def instant_value(
    payload: ValuationRequest,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    """Same calculation, not persisted — for quick previews before committing."""
    return await service.instant_value(UUID(current_user.id), payload)
