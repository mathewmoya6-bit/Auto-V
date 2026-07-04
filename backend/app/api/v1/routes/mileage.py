# app/api/v1/routes/mileage.py
# =============================================================================
# AUTO-V API - Mileage Routes
# =============================================================================

import logging
from datetime import date as date_type
from datetime import datetime
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.mileage import VehicleCategory, VehicleVariant, Route, MileageClaim
from app.api.v1.routes.auth import get_current_user
from app.models.user import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mileage", tags=["Mileage"])


# ─── Helper Functions ──────────────────────────────────────────────────

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


def claim_to_dict(claim: MileageClaim) -> Dict[str, Any]:
    """Convert claim to dictionary with proper formatting"""
    return {
        "id": str(claim.id),
        "user_id": str(claim.user_id),
        "vehicle_id": str(claim.vehicle_id) if claim.vehicle_id else None,
        "trip_date": claim.trip_date.isoformat() if claim.trip_date else None,
        "start_location": claim.start_location,
        "end_location": claim.end_location,
        "distance_km": float(claim.distance_km) if claim.distance_km else 0,
        "vehicle_category": claim.vehicle_category,
        "rate_per_km": float(claim.rate_per_km) if claim.rate_per_km else 0,
        "claim_amount": float(claim.claim_amount) if claim.claim_amount else 0,
        "purpose": claim.purpose,
        "notes": claim.notes,
        "status": claim.status,
        "approved_by": str(claim.approved_by) if claim.approved_by else None,
        "approved_at": claim.approved_at.isoformat() if claim.approved_at else None,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
    }


# ─── Public Endpoints ──────────────────────────────────────────────────

@router.get("/categories", response_model=List[Dict[str, Any]])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    include_inactive: bool = Query(False, description="Include inactive categories"),
):
    """Get all vehicle categories with their variants"""
    try:
        logger.info("Fetching categories from database...")
        
        # Build query
        query = select(VehicleCategory)
        if not include_inactive:
            query = query.where(VehicleCategory.is_active == True)
        query = query.options(selectinload(VehicleCategory.variants)).order_by(VehicleCategory.name)
        
        result = await db.execute(query)
        categories = result.scalars().all()
        
        if not categories:
            logger.warning("No categories found in database")
            return []
        
        response = []
        for cat in categories:
            # Filter variants based on active status
            variants = cat.variants
            if not include_inactive:
                variants = [v for v in variants if v.is_active]
            sorted_variants = sorted(variants, key=lambda v: v.label or "")
            
            response.append({
                "id": str(cat.id),
                "label": cat.name or "Unnamed",
                "fuel_type": cat.fuel_type or "—",
                "is_active": cat.is_active,
                "variants": [variant_to_dict(v, cat.name) for v in sorted_variants],
            })
        
        logger.info(f"Returning {len(response)} categories with variants")
        return response
        
    except Exception as e:
        logger.exception("Failed to fetch categories")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch categories: {str(e)}"
        )


@router.get("/categories/{category_id}/variants", response_model=List[Dict[str, Any]])
async def get_category_variants(
    category_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all variants for a specific category"""
    try:
        result = await db.execute(
            select(VehicleVariant)
            .where(VehicleVariant.category_id == category_id)
            .where(VehicleVariant.is_active == True)
            .order_by(VehicleVariant.label)
        )
        variants = result.scalars().all()
        
        if not variants:
            return []
        
        # Get category name
        cat_result = await db.execute(
            select(VehicleCategory).where(VehicleCategory.id == category_id)
        )
        category = cat_result.scalar_one_or_none()
        category_name = category.name if category else "Unknown"
        
        return [variant_to_dict(v, category_name) for v in variants]
        
    except Exception as e:
        logger.exception(f"Failed to fetch variants for category {category_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch variants: {str(e)}"
        )


@router.get("/routes", response_model=List[Dict[str, Any]])
async def get_routes(
    db: AsyncSession = Depends(get_db),
    include_inactive: bool = Query(False, description="Include inactive routes"),
):
    """Get all active routes"""
    try:
        logger.info("Fetching routes from database...")
        
        query = select(Route)
        if not include_inactive:
            query = query.where(Route.is_active == True)
        query = query.order_by(Route.from_city, Route.to_city)
        
        result = await db.execute(query)
        routes = result.scalars().all()
        
        response = [
            {
                "id": str(r.id),
                "from_city": r.from_city,
                "to_city": r.to_city,
                "km": float(r.km) if r.km is not None else 0.0,
                "is_active": r.is_active,
            }
            for r in routes
        ]
        
        logger.info(f"Returning {len(response)} routes")
        return response
        
    except Exception as e:
        logger.exception("Failed to fetch routes")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch routes: {str(e)}"
        )


@router.get("/calculate")
async def calculate_mileage(
    category_id: str = Query(..., description="Vehicle category ID"),
    variant_id: str = Query(..., description="Vehicle variant ID"),
    distance_km: float = Query(..., gt=0, description="Distance in kilometers"),
    db: AsyncSession = Depends(get_db),
):
    """Calculate mileage cost for a specific vehicle variant"""
    try:
        # Get the variant
        result = await db.execute(
            select(VehicleVariant)
            .where(VehicleVariant.id == variant_id)
            .where(VehicleVariant.is_active == True)
        )
        variant = result.scalar_one_or_none()
        
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variant not found"
            )
        
        # Calculate costs
        fixed_cost = variant.fixed_per_km * distance_km
        operating_cost = variant.operating_per_km * distance_km
        total_cost = variant.total_per_km * distance_km
        
        return {
            "variant_id": str(variant.id),
            "variant_label": variant.label,
            "distance_km": distance_km,
            "fixed_per_km": float(variant.fixed_per_km),
            "operating_per_km": float(variant.operating_per_km),
            "total_per_km": float(variant.total_per_km),
            "fixed_cost": float(fixed_cost),
            "operating_cost": float(operating_cost),
            "total_cost": float(total_cost),
            "components": variant.components or {},
            "yearly_costs": {
                "year1": float(variant.year1) if variant.year1 else 0,
                "year2": float(variant.year2) if variant.year2 else 0,
                "year3": float(variant.year3) if variant.year3 else 0,
                "year4": float(variant.year4) if variant.year4 else 0,
                "year5": float(variant.year5) if variant.year5 else 0,
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to calculate mileage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate mileage: {str(e)}"
        )


# ─── Claim Endpoints ──────────────────────────────────────────────────

class ClaimCreateRequest(BaseModel):
    trip_date: date_type
    start_location: Optional[str] = Field(None, max_length=255)
    end_location: Optional[str] = Field(None, max_length=255)
    distance_km: float = Field(..., gt=0, description="Distance in kilometers")
    vehicle_category: Optional[str] = Field(None, max_length=50)
    rate_per_km: float = Field(..., gt=0, description="Rate per kilometer")
    purpose: Optional[str] = Field(None, max_length=100)
    vehicle_id: Optional[str] = Field(None, description="Vehicle UUID")
    notes: Optional[str] = Field(None, max_length=500)


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
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


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
            notes=payload.notes,
            status="pending",
        )
        
        db.add(claim)
        await db.commit()
        await db.refresh(claim)
        
        logger.info(f"Claim created successfully: {claim.id} for user {current_user.id}")
        return ClaimResponse(**claim_to_dict(claim))
        
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create claim")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create claim: {str(e)}"
        )


@router.get("/claims", response_model=List[ClaimResponse])
async def list_my_claims(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500, description="Number of claims to return"),
    offset: int = Query(0, ge=0, description="Number of claims to skip"),
):
    """List all claims for the current user with pagination"""
    try:
        query = select(MileageClaim).where(MileageClaim.user_id == current_user.id)
        
        if status_filter:
            query = query.where(MileageClaim.status == status_filter)
        
        query = query.order_by(MileageClaim.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        claims = result.scalars().all()
        
        logger.info(f"Found {len(claims)} claims for user {current_user.id}")
        return [ClaimResponse(**claim_to_dict(c)) for c in claims]
        
    except Exception as e:
        logger.exception("Failed to fetch claims")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch claims: {str(e)}"
        )


@router.get("/claims/count")
async def get_claims_count(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
):
    """Get count of claims for the current user"""
    try:
        query = select(func.count()).select_from(MileageClaim).where(MileageClaim.user_id == current_user.id)
        
        if status_filter:
            query = query.where(MileageClaim.status == status_filter)
        
        result = await db.execute(query)
        count = result.scalar()
        
        return {"count": count}
        
    except Exception as e:
        logger.exception("Failed to get claims count")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get claims count: {str(e)}"
        )


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Get a specific claim by ID"""
    try:
        result = await db.execute(
            select(MileageClaim).where(MileageClaim.id == claim_id)
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
        
        return ClaimResponse(**claim_to_dict(claim))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to fetch claim {claim_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch claim: {str(e)}"
        )


@router.put("/claims/{claim_id}")
async def update_claim(
    claim_id: str,
    update_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Update a claim (only pending claims can be updated)"""
    try:
        result = await db.execute(
            select(MileageClaim).where(MileageClaim.id == claim_id)
        )
        claim = result.scalar_one_or_none()
        
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Claim not found"
            )
        
        # Check if user owns this claim
        if claim.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this claim"
            )
        
        # Only allow updates if claim is pending
        if claim.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update claim with status: {claim.status}"
            )
        
        # Update allowed fields
        allowed_fields = ["start_location", "end_location", "distance_km", "purpose", "notes"]
        for field in allowed_fields:
            if field in update_data:
                setattr(claim, field, update_data[field])
        
        # Recalculate claim amount if distance or rate changed
        if "distance_km" in update_data or "rate_per_km" in update_data:
            distance = update_data.get("distance_km", claim.distance_km)
            rate = update_data.get("rate_per_km", claim.rate_per_km)
            claim.claim_amount = round(distance * rate, 2)
        
        await db.commit()
        await db.refresh(claim)
        
        logger.info(f"Claim {claim_id} updated by user {current_user.id}")
        return ClaimResponse(**claim_to_dict(claim))
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to update claim {claim_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update claim: {str(e)}"
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
            select(MileageClaim).where(MileageClaim.id == claim_id)
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
        return ClaimResponse(**claim_to_dict(claim))
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to update claim {claim_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update claim: {str(e)}"
        )


@router.delete("/claims/{claim_id}")
async def delete_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    """Delete a claim (only pending claims can be deleted)"""
    try:
        result = await db.execute(
            select(MileageClaim).where(MileageClaim.id == claim_id)
        )
        claim = result.scalar_one_or_none()
        
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Claim not found"
            )
        
        # Check if user owns this claim
        if claim.user_id != current_user.id and not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this claim"
            )
        
        # Only allow deletion if claim is pending
        if claim.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete claim with status: {claim.status}"
            )
        
        await db.delete(claim)
        await db.commit()
        
        logger.info(f"Claim {claim_id} deleted by user {current_user.id}")
        return {"message": "Claim deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to delete claim {claim_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete claim: {str(e)}"
        )
