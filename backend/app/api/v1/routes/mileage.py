# app/api/v1/routes/mileage.py
# =============================================================================
# AUTO-V API - Mileage Routes
# =============================================================================
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token, get_current_admin_user, get_current_user
from app.schemas.mileage import (
    MileageApprovalRequest,
    MileageCalculateRequest,
    MileageCalculateResponse,
    MileageClaimCreate,
    MileageClaimResponse,
    MileageClaimSummary,
    MileageClaimUpdate,
    RouteResponse,
    VehicleCategoryResponse,
    VehicleVariantResponse,
)
from app.schemas.user import UserProfile
from app.services.mileage_service import MileageService

router = APIRouter(tags=["Mileage"])

_optional_bearer = HTTPBearer(auto_error=False)


def get_mileage_service() -> MileageService:
    return MileageService()


async def _optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
) -> Optional[str]:
    """calculate_trip_cost stays public — this only attaches a user id for
    logging when a valid token happens to be present, matching the
    original calculate.py behavior."""
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    return payload.get("sub") if payload else None


# ─── Reference data ──────────────────────────────────────────────────

@router.get("/categories", response_model=List[VehicleCategoryResponse])
async def list_categories(service: MileageService = Depends(get_mileage_service)):
    """Get all vehicle categories"""
    return await service.list_categories()


@router.get("/variants", response_model=List[VehicleVariantResponse])
async def list_variants(
    category_id: Optional[UUID] = Query(None),
    service: MileageService = Depends(get_mileage_service),
):
    """Get vehicle variants, optionally filtered by category"""
    return await service.list_variants(category_id)


@router.get("/variants/{variant_id}", response_model=VehicleVariantResponse)
async def get_variant(
    variant_id: UUID, 
    service: MileageService = Depends(get_mileage_service)
):
    """Get a specific vehicle variant"""
    return await service.get_variant(variant_id)


@router.get("/routes", response_model=List[RouteResponse])
async def list_routes(service: MileageService = Depends(get_mileage_service)):
    """Get all available routes"""
    return await service.list_routes()


# ─── Trip cost calculation — public, optional auth ───────────────────

@router.post("/calculate", response_model=MileageCalculateResponse)
async def calculate_trip_cost(
    request: MileageCalculateRequest,
    user_id: Optional[str] = Depends(_optional_user_id),
    service: MileageService = Depends(get_mileage_service),
):
    """Calculate mileage trip cost (public endpoint, optional auth)"""
    return await service.calculate_trip_cost(request, user_id)


# ─── Claims ────────────────────────────────────────────────────────────

@router.post("/claims", response_model=MileageClaimResponse, status_code=201)
async def create_claim(
    payload: MileageClaimCreate,
    current_user: UserProfile = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    """Create a new mileage claim"""
    return await service.create_claim(UUID(current_user.id), payload)


@router.get("/claims", response_model=List[MileageClaimResponse])
async def list_claims(
    current_user: UserProfile = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    """Get all mileage claims for the current user"""
    return await service.list_claims(UUID(current_user.id))


@router.get("/claims/summary", response_model=MileageClaimSummary)
async def claims_summary(
    current_user: UserProfile = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    """Get mileage claims summary"""
    return await service.claims_summary(UUID(current_user.id))


@router.get("/claims/{claim_id}", response_model=MileageClaimResponse)
async def get_claim(
    claim_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    """Get a specific mileage claim by ID"""
    is_admin = current_user.role == "admin"
    return await service.get_claim(claim_id, UUID(current_user.id), is_admin)


@router.patch("/claims/{claim_id}", response_model=MileageClaimResponse)
async def update_claim(
    claim_id: UUID,
    payload: MileageClaimUpdate,
    current_user: UserProfile = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    """Update a mileage claim"""
    is_admin = current_user.role == "admin"
    return await service.update_claim(claim_id, UUID(current_user.id), payload, is_admin)


@router.post("/claims/{claim_id}/approve", response_model=MileageClaimResponse)
async def approve_claim(
    claim_id: UUID,
    payload: MileageApprovalRequest,
    current_admin: UserProfile = Depends(get_current_admin_user),
    service: MileageService = Depends(get_mileage_service),
):
    """Approve a mileage claim (admin only)"""
    return await service.approve_claim(claim_id, UUID(current_admin.id), payload)


@router.get("/vehicles/{vehicle_id}/mileage", response_model=List[MileageClaimResponse])
async def get_vehicle_mileage(
    vehicle_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    """Get mileage history for a specific vehicle"""
    return await service.get_vehicle_mileage(vehicle_id, UUID(current_user.id))


@router.post("/vehicles/{vehicle_id}/mileage", response_model=MileageClaimResponse)
async def add_mileage_entry(
    vehicle_id: UUID,
    payload: MileageClaimCreate,
    current_user: UserProfile = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    """Add a mileage entry for a specific vehicle"""
    return await service.add_mileage_entry(vehicle_id, UUID(current_user.id), payload)


@router.get("/latest", response_model=List[MileageClaimResponse])
async def get_latest_mileage_entries(
    current_user: UserProfile = Depends(get_current_user),
    limit: int = 10,
    service: MileageService = Depends(get_mileage_service),
):
    """Get latest mileage entries across all vehicles"""
    return await service.get_latest_entries(UUID(current_user.id), limit)
