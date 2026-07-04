# app/api/v1/routes/mileage.py
# =============================================================================
# AUTO-V API - Mileage Routes
# =============================================================================

import logging
from datetime import date as date_type
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
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
    return {
        "id": str(variant.id),
        "label": variant.label,
        "category_id": str(variant.category_id),
        "category_name": category_name,
        "fixed_per_km": float(variant.fixed_per_km) if variant.fixed_per_km else 0,
        "operating_per_km": float(variant.operating_per_km) if variant.operating_per_km else 0,
        "total_per_km": float(variant.total_per_km) if variant.total_per_km else 0,
        "initial_cost": float(variant.initial_cost) if variant.initial_cost else 0,
        "year1": float(variant.year1) if variant.year1 else 0,
        "year2": float(variant.year2) if variant.year2 else 0,
        "year3": float(variant.year3) if variant.year3 else 0,
        "year4": float(variant.year4) if variant.year4 else 0,
        "year5": float(variant.year5) if variant.year5 else 0,
        "components": variant.components or {},
    }


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(VehicleCategory)
            .where(VehicleCategory.is_active == True)  # noqa: E712
            .options(selectinload(VehicleCategory.variants))
            .order_by(VehicleCategory.name)
        )
        categories = result.scalars().all()

        response = []
        for cat in categories:
            active_variants = sorted([v for v in cat.variants if v.is_active], key=lambda v: v.label)
            response.append({
                "id": str(cat.id),
                "label": cat.name,
                "fuel_type": cat.fuel_type or "—",
                "variants": [variant_to_dict(v, cat.name) for v in active_variants],
            })
        return response
    except Exception as e:
        logger.error(f"Error fetching categories: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch categories")


@router.get("/routes")
async def get_routes(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Route).where(Route.is_active == True).order_by(Route.from_city, Route.to_city)  # noqa: E712
        )
        routes = result.scalars().all()
        return [{"from_city": r.from_city, "to_city": r.to_city, "km": float(r.km)} for r in routes]
    except Exception as e:
        logger.error(f"Error fetching routes: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch routes")


class ClaimCreateRequest(BaseModel):
    trip_date: date_type
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    distance_km: float
    vehicle_category: Optional[str] = None
    rate_per_km: float
    purpose: Optional[str] = None
    vehicle_id: Optional[str] = None


@router.post("/claims", status_code=status.HTTP_201_CREATED)
async def create_claim(
    payload: ClaimCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    claim = MileageClaim(
        user_id=current_user.id,
        vehicle_id=payload.vehicle_id,
        trip_date=payload.trip_date,
        start_location=payload.start_location,
        end_location=payload.end_location,
        distance_km=payload.distance_km,
        vehicle_category=payload.vehicle_category,
        rate_per_km=payload.rate_per_km,
        claim_amount=round(payload.distance_km * payload.rate_per_km, 2),
        purpose=payload.purpose,
        status="pending",
    )
    db.add(claim)
    try:
        await db.commit()
        await db.refresh(claim)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create claim: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create claim")

    return claim.to_dict()


@router.get("/claims")
async def list_my_claims(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
):
    result = await db.execute(
        select(MileageClaim).where(MileageClaim.user_id == current_user.id).order_by(MileageClaim.created_at.desc())
    )
    return [c.to_dict() for c in result.scalars().all()]
