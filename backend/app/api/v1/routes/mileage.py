# app/api/v1/routes/mileage.py
# =============================================================================
# AUTO-V API - Mileage Routes
# =============================================================================

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.mileage import VehicleCategory, VehicleVariant, Route

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mileage", tags=["Mileage"])


def variant_to_dict(variant: VehicleVariant, category_name: str) -> Dict[str, Any]:
    """Convert VehicleVariant ORM object to dictionary."""
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
    """Get all vehicle categories with their variants from the database."""
    try:
        logger.info("📊 Fetching mileage categories from database...")
        
        result = await db.execute(
            select(VehicleCategory)
            .where(VehicleCategory.is_active == True)
            .order_by(VehicleCategory.name)
        )
        categories = result.scalars().all()
        
        response = []
        for cat in categories:
            variants_result = await db.execute(
                select(VehicleVariant)
                .where(VehicleVariant.category_id == cat.id)
                .where(VehicleVariant.is_active == True)
                .order_by(VehicleVariant.label)
            )
            variants = variants_result.scalars().all()
            
            response.append({
                "id": str(cat.id),
                "label": cat.name,
                "fuel_type": cat.fuel_type or "—",
                "variants": [variant_to_dict(v, cat.name) for v in variants],
            })
        
        logger.info(f"✅ Fetched {len(response)} categories")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch categories: {str(e)}"
        )


@router.get("/routes")
async def get_routes(db: AsyncSession = Depends(get_db)):
    """Get all quick routes with distances from the database."""
    try:
        logger.info("📍 Fetching mileage routes from database...")
        
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
                "km": float(r.km),
            }
            for r in routes
        ]
        
        logger.info(f"✅ Fetched {len(response)} routes")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching routes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch routes: {str(e)}"
        )
