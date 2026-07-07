# app/api/v1/routes/mileage.py
# =============================================================================
# AUTO-V API - Mileage Routes
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List

from app.services.mileage_service import MileageService
from app.schemas.mileage import (
    VehicleCategoryCreate,
    VehicleCategoryResponse,
    VehicleVariantCreate,
    VehicleVariantResponse,
    RouteCreate,
    RouteResponse,
    MileageClaimCreate,
    MileageClaimResponse,
)

router = APIRouter(tags=["Mileage"])
service = MileageService()


# ─── Categories ──────────────────────────────────────────────────────

@router.get("/categories", response_model=List[VehicleCategoryResponse])
async def get_categories(active_only: bool = Query(True)):
    """Get all vehicle categories."""
    try:
        return service.get_categories(active_only)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/categories", response_model=VehicleCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(data: VehicleCategoryCreate):
    """Create a new vehicle category."""
    try:
        return service.create_category(data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ─── Variants ────────────────────────────────────────────────────────

@router.get("/variants", response_model=List[VehicleVariantResponse])
async def get_variants(category_id: Optional[str] = Query(None)):
    """Get vehicle variants."""
    try:
        return service.get_variants(category_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/variants", response_model=VehicleVariantResponse, status_code=status.HTTP_201_CREATED)
async def create_variant(data: VehicleVariantCreate):
    """Create a new vehicle variant."""
    try:
        return service.create_variant(data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ─── Routes ──────────────────────────────────────────────────────────

@router.get("/routes", response_model=List[RouteResponse])
async def get_routes(active_only: bool = Query(True)):
    """Get all routes."""
    try:
        return service.get_routes(active_only)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/routes", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def create_route(data: RouteCreate):
    """Create a new route."""
    try:
        return service.create_route(data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ─── Claims ──────────────────────────────────────────────────────────

@router.get("/claims", response_model=List[MileageClaimResponse])
async def get_claims(user_id: Optional[str] = Query(None)):
    """Get mileage claims."""
    try:
        return service.get_claims(user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/claims", response_model=MileageClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(data: MileageClaimCreate):
    """Submit a mileage claim."""
    try:
        return service.create_claim(data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/claims/{claim_id}/approve", response_model=MileageClaimResponse)
async def approve_claim(claim_id: str, approver_id: str):
    """Approve a mileage claim."""
    try:
        return service.approve_claim(claim_id, approver_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


__all__ = ["router"]
