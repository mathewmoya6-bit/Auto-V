# app/api/v1/routes/mileage.py
# =============================================================================
# AUTO-V API - Mileage Routes (Database-Backed)
# =============================================================================

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional

from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mileage", tags=["Mileage"])


# ─── Helper Functions ──────────────────────────────────────────────

async def get_categories_from_db(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Fetch all vehicle categories with their variants from the database.
    """
    from sqlalchemy import text
    
    # Raw SQL query to get categories with variants
    query = text("""
        SELECT 
            c.id as category_id,
            c.name as category_name,
            c.fuel_type,
            v.id as variant_id,
            v.label as variant_label,
            v.fixed_per_km,
            v.operating_per_km,
            v.total_per_km,
            v.initial_cost,
            v.year1,
            v.year2,
            v.year3,
            v.year4,
            v.year5,
            v.components
        FROM vehicle_categories c
        LEFT JOIN vehicle_variants v ON c.id = v.category_id
        WHERE c.is_active = true AND (v.is_active = true OR v.id IS NULL)
        ORDER BY c.name, v.label
    """)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    # Build category structure
    categories_map = {}
    for row in rows:
        category_id = str(row.category_id)
        if category_id not in categories_map:
            categories_map[category_id] = {
                "id": category_id,
                "label": row.category_name,
                "fuel_type": row.fuel_type or "—",
                "variants": []
            }
        
        # Add variant if exists
        if row.variant_id:
            variant = {
                "id": str(row.variant_id),
                "label": row.variant_label,
                "category_id": category_id,
                "category_name": row.category_name,
                "fixed_per_km": float(row.fixed_per_km) if row.fixed_per_km else 0,
                "operating_per_km": float(row.operating_per_km) if row.operating_per_km else 0,
                "total_per_km": float(row.total_per_km) if row.total_per_km else 0,
                "initial_cost": float(row.initial_cost) if row.initial_cost else 0,
                "year1": float(row.year1) if row.year1 else 0,
                "year2": float(row.year2) if row.year2 else 0,
                "year3": float(row.year3) if row.year3 else 0,
                "year4": float(row.year4) if row.year4 else 0,
                "year5": float(row.year5) if row.year5 else 0,
                "components": row.components or {}
            }
            categories_map[category_id]["variants"].append(variant)
    
    return list(categories_map.values())


async def get_routes_from_db(db: AsyncSession) -> List[Dict[str, Any]]:
    """Fetch all routes from the database."""
    from sqlalchemy import text
    
    query = text("""
        SELECT from_city, to_city, km
        FROM routes
        WHERE is_active = true
        ORDER BY from_city, to_city
    """)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    return [
        {"from_city": row.from_city, "to_city": row.to_city, "km": float(row.km)}
        for row in rows
    ]


# ─── PUBLIC API ENDPOINTS ────────────────────────────────────────────

@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """
    Get all vehicle categories with their variants from the database.
    """
    try:
        logger.info("📊 Fetching mileage categories from database...")
        
        categories = await get_categories_from_db(db)
        
        logger.info(f"✅ Fetched {len(categories)} categories")
        return categories
        
    except Exception as e:
        logger.error(f"❌ Error fetching categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch categories: {str(e)}"
        )


@router.get("/routes")
async def get_routes(db: AsyncSession = Depends(get_db)):
    """
    Get all quick routes with distances from the database.
    """
    try:
        logger.info("📍 Fetching mileage routes from database...")
        
        routes = await get_routes_from_db(db)
        
        logger.info(f"✅ Fetched {len(routes)} routes")
        return routes
        
    except Exception as e:
        logger.error(f"❌ Error fetching routes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch routes: {str(e)}"
        )


@router.get("/rates")
async def get_mileage_rates(db: AsyncSession = Depends(get_db)):
    """Get all mileage rates (flattened view)."""
    try:
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                c.name as category,
                v.label as variant,
                v.total_per_km as rate_per_km,
                v.fixed_per_km,
                v.operating_per_km,
                c.fuel_type
            FROM vehicle_categories c
            JOIN vehicle_variants v ON c.id = v.category_id
            WHERE c.is_active = true AND v.is_active = true
            ORDER BY c.name, v.label
        """)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        rates = [
            {
                "category": row.category,
                "variant": row.variant,
                "rate_per_km": float(row.rate_per_km) if row.rate_per_km else 0,
                "fixed_per_km": float(row.fixed_per_km) if row.fixed_per_km else 0,
                "operating_per_km": float(row.operating_per_km) if row.operating_per_km else 0,
                "fuel_type": row.fuel_type or "—",
            }
            for row in rows
        ]
        
        return rates
        
    except Exception as e:
        logger.error(f"❌ Error fetching rates: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rates: {str(e)}"
        )


@router.get("/calculate")
async def calculate_mileage(
    category_id: str,
    variant_id: str,
    distance_km: float,
    db: AsyncSession = Depends(get_db),
):
    """Calculate mileage cost for a specific vehicle and distance."""
    try:
        from sqlalchemy import text
        
        if distance_km <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Distance must be greater than 0"
            )
        
        # Fetch variant data
        query = text("""
            SELECT 
                c.name as category_name,
                v.label as variant_label,
                v.fixed_per_km,
                v.operating_per_km,
                v.total_per_km,
                v.initial_cost,
                v.year1,
                v.year2,
                v.year3,
                v.year4,
                v.year5,
                v.components
            FROM vehicle_variants v
            JOIN vehicle_categories c ON v.category_id = c.id
            WHERE v.id = :variant_id AND v.is_active = true
        """)
        
        result = await db.execute(query, {"variant_id": variant_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle variant not found"
            )
        
        fixed_cost = (float(row.fixed_per_km) if row.fixed_per_km else 0) * distance_km
        operating_cost = (float(row.operating_per_km) if row.operating_per_km else 0) * distance_km
        total_cost = (float(row.total_per_km) if row.total_per_km else 0) * distance_km
        
        return {
            "category": row.category_name,
            "variant": row.variant_label,
            "distance_km": distance_km,
            "fixed_per_km": float(row.fixed_per_km) if row.fixed_per_km else 0,
            "operating_per_km": float(row.operating_per_km) if row.operating_per_km else 0,
            "total_per_km": float(row.total_per_km) if row.total_per_km else 0,
            "fixed_cost": round(fixed_cost, 2),
            "operating_cost": round(operating_cost, 2),
            "total_cost": round(total_cost, 2),
            "components": row.components or {},
            "years": {
                "year1": float(row.year1) if row.year1 else 0,
                "year2": float(row.year2) if row.year2 else 0,
                "year3": float(row.year3) if row.year3 else 0,
                "year4": float(row.year4) if row.year4 else 0,
                "year5": float(row.year5) if row.year5 else 0,
            },
            "initial_cost": float(row.initial_cost) if row.initial_cost else 0,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error calculating mileage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate mileage: {str(e)}"
        )
