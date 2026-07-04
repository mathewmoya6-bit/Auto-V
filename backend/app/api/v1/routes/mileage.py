# app/api/v1/routes/mileage.py
# =============================================================================
# AUTO-V API - Mileage Routes
# =============================================================================

import logging
from datetime import date as date_type
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.mileage import VehicleCategory, VehicleVariant, Route, MileageClaim
from app.api.v1.routes.auth import get_current_user
from app.models.user import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mileage", tags=["Mileage"])


def variant_to_dict(variant: VehicleVariant, category_name: str) -> Dict[str, Any]:
    """Convert variant to dictionary with proper type handling"""
    # Safely handle components
    components = variant.components or {}
    if not isinstance(components, dict):
        components = {}
    
    return {
        "id": str(variant.id),
        "label": variant.label or "Unnamed",
        "category_id": str(variant.category_id),
        "category_name": category_name,
        "fixed_per_km": float(variant.fixed_per_km) if variant.fixed_per_km is not None else 0.0,
        "operating_per_km": float(variant.operating_per_km) if variant.operating_per_km is not None else 0.0,
        "total_per_km": float(variant.total_per_km) if variant.total_per_km is not None else 0.0,
        "initial_cost": float(variant.initial_cost) if variant.initial_cost is not None else 0.0,
        "year1": float(variant.year1) if variant.year1 is not None else 0.0,
        "year2": float(variant.year2) if variant.year2 is not None else 0.0,
        "year3": float(variant.year3) if variant.year3 is not None else 0.0,
        "year4": float(variant.year4) if variant.year4 is not None else 0.0,
        "year5": float(variant.year5) if variant.year5 is not None else 0.0,
        "components": {
            "insurance": float(components.get("insurance", 0)),
            "depreciation": float(components.get("depreciation", 0)),
            "interest": float(components.get("interest", 0)),
            "fuel": float(components.get("fuel", 0)),
            "servicing": float(components.get("servicing", 0)),
            "repairs": float(components.get("repairs", 0)),
            "tyres": float(components.get("tyres", 0)),
            "licences": float(components.get("licences", 0)),
        },
        "is_active": variant.is_active,
    }


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all vehicle categories with their variants"""
    try:
        logger.info("Fetching categories from database...")
        
        # Fetch categories with their variants
        result = await db.execute(
            select(VehicleCategory)
            .where(VehicleCategory.is_active == True)
            .options(selectinload(VehicleCategory.variants))
            .order_by(VehicleCategory.name)
        )
        categories = result.scalars().all()
        
        if not categories:
            logger.warning("No active categories found in database")
            return []
        
        response = []
        for cat in categories:
            # Filter active variants and sort by label
            active_variants = [v for v in cat.variants if v.is_active]
            sorted_variants = sorted(active_variants, key=lambda v: v.label or "")
            
            response.append({
                "id": str(cat.id),
                "label": cat.name or "Unnamed",
                "fuel_type": cat.fuel_type or "—",
                "variants": [variant_to_dict(v, cat.name) for v in sorted_variants],
            })
        
        logger.info(f"Returning {len(response)} categories with variants")
        return response
        
    except Exception as e:
        logger.exception("Failed to fetch categories")  # This logs the full traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)  # Expose the real error
        )


@router.get("/routes")
async def get_routes(db: AsyncSession = Depends(get_db)):
    """Get all active routes"""
    try:
        logger.info("Fetching routes from database...")
        result = await db.execute(
            select(Route)
            .where(Route.is_active == True)
            .order_by(Route.from_city, Route.to_city)
        )
        routes = result.scalars().all()
        
        response = [
            {
                "from_city": r.from_city,
                "to_city": r.to_city,
                "km": float(r.km) if r.km is not None else 0.0
            }
            for r in routes
        ]
        
        logger.info(f"Returning {len(response)} routes")
        return response
        
    except Exception as e:
        logger.exception("Failed to fetch routes")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


class ClaimCreateRequest(BaseModel):
    trip_date: date_type
    start_location: Optional[str] = Field(None, max_length=255)
    end_location: Optional[str] = Field(None, max_length=255)
    distance_km: float = Field(..., gt=0, description="Distance in kilometers")
    vehicle_category: Optional[str] = Field(None, max_length=50)
    rate_per_km: float = Field(..., gt=0, description="Rate per kilometer")
    purpose: Optional[str] = Field(None, max_length=100)
    vehicle_id: Optional[str] = Field(None, description="Vehicle UUID")


class ClaimResponse(BaseModel):
    id: str
    user_id: str
    vehicle_id: Optional[str]
    trip_date: date_type
    start_location: Optional[str]
    end_location: Optional[str]
    distance_km: float
    vehicle_category: Optional[str]
    rate_per_km: float
    claim_amount: float
    purpose: Optional[str]
    notes: Optional[str]
    status: str
    created_at: Optional[str]


@router.post("/claims", status_code=status.HTTP_201_CREATED, response_model=ClaimResponse)
async def create_claim(
    payload: ClaimCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Create a new mileage claim"""
    try:
        claim_amount = round(payload.distance_km * payload.rate_per_km, 2)
        
        claim = MileageClaim(
            user_id=current_user.id,
            vehicle_id=payload.vehicle_id,
            trip_date=payload.trip_date,
            start_location=payload.start_location,
            end_location=payload.end_location,
            distance_km=payload.distance_km,
            vehicle_category=payload.vehicle_category,
            rate_per_km=payload.rate_per_km,
            claim_amount=claim_amount,
            purpose=payload.purpose,
            status="pending",
        )
        
        db.add(claim)
        await db.commit()
        await db.refresh(claim)
        
        logger.info(f"Claim created successfully: {claim.id} for user {current_user.id}")
        return ClaimResponse(**claim.to_dict())
        
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create claim")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/claims", response_model=list[ClaimResponse])
async def list_my_claims(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """List all claims for the current user"""
    try:
        result = await db.execute(
            select(MileageClaim)
            .where(MileageClaim.user_id == current_user.id)
            .order_by(MileageClaim.created_at.desc())
        )
        claims = result.scalars().all()
        
        logger.info(f"Found {len(claims)} claims for user {current_user.id}")
        return [ClaimResponse(**c.to_dict()) for c in claims]
        
    except Exception as e:
        logger.exception("Failed to fetch claims")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/claims/{claim_id}")
async def get_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Get a specific claim by ID"""
    try:
        result = await db.execute(
            select(MileageClaim)
            .where(MileageClaim.id == claim_id)
        )
        claim = result.scalar_one_or_none()
        
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Claim not found"
            )
        
        # Check if user owns this claim or is admin
        if claim.user_id != current_user.id and not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this claim"
            )
        
        return claim.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to fetch claim {claim_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/claims/{claim_id}/status")
async def update_claim_status(
    claim_id: str,
    status_update: dict,  # {"status": "approved"} or {"status": "rejected"}
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Update claim status (admin/approver only)"""
    try:
        # Check if user has permission
        if not current_user.is_admin() and current_user.role not in ["manager", "approver"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update claim status"
            )
        
        result = await db.execute(
            select(MileageClaim)
            .where(MileageClaim.id == claim_id)
        )
        claim = result.scalar_one_or_none()
        
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Claim not found"
            )
        
        new_status = status_update.get("status")
        if new_status not in ["pending", "approved", "rejected", "paid", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be one of: pending, approved, rejected, paid, cancelled"
            )
        
        claim.status = new_status
        if new_status in ["approved", "rejected"]:
            claim.approved_by = current_user.id
            claim.approved_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(claim)
        
        logger.info(f"Claim {claim_id} status updated to {new_status} by {current_user.id}")
        return claim.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to update claim {claim_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
