# app/api/v1/routes/mileage.py
# =============================================================================
# Mileage Routes - Vehicle Categories, Variants, and Cost Calculation
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.models.mileage import VehicleCategory, VehicleVariant

router = APIRouter()

# ─── Pydantic Models ─────────────────────────────────────────────────

class CategoryResponse(BaseModel):
    id: str
    name: str
    fuel_type: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True

class VehicleVariantResponse(BaseModel):
    id: str
    category_id: str
    label: str
    fixed_per_km: Optional[float] = None
    operating_per_km: Optional[float] = None
    total_per_km: Optional[float] = None
    initial_cost: Optional[float] = None
    components: Optional[dict] = None
    is_active: bool = True

    class Config:
        from_attributes = True

class CalculateRequest(BaseModel):
    vehicle_id: str
    distance_km: float

class CalculateResponse(BaseModel):
    total_cost: float
    per_km: float
    fixed_per_km: float
    operating_per_km: float
    fixed_total: float
    operating_total: float
    yearly_projection: List[float]

# ─── Routes ─────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all vehicle categories
    """
    try:
        result = await db.execute(
            select(VehicleCategory)
            .where(VehicleCategory.is_active == True)
            .order_by(VehicleCategory.name)
        )
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")

@router.get("/vehicles", response_model=List[VehicleVariantResponse])
async def get_vehicles(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all vehicle variants with optional filters
    """
    try:
        query = select(VehicleVariant).where(VehicleVariant.is_active == True)
        
        if category_id:
            query = query.where(VehicleVariant.category_id == category_id)
            
        query = query.order_by(VehicleVariant.label)
        
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching vehicles: {str(e)}")

@router.get("/vehicles/{vehicle_id}", response_model=VehicleVariantResponse)
async def get_vehicle(
    vehicle_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single vehicle variant by ID
    """
    try:
        result = await db.execute(
            select(VehicleVariant).where(VehicleVariant.id == vehicle_id)
        )
        vehicle = result.scalar_one_or_none()
        if not vehicle:
            raise HTTPException(status_code=404, detail=f"Vehicle with ID {vehicle_id} not found")
        return vehicle
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching vehicle: {str(e)}")

@router.post("/calculate", response_model=CalculateResponse)
async def calculate_cost(
    request: CalculateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate running costs for a vehicle over a given distance
    """
    try:
        # Get vehicle from database
        result = await db.execute(
            select(VehicleVariant).where(VehicleVariant.id == request.vehicle_id)
        )
        vehicle = result.scalar_one_or_none()
        
        if not vehicle:
            raise HTTPException(status_code=404, detail=f"Vehicle with ID {request.vehicle_id} not found")
        
        # Use the pre-calculated rates from the database
        fixed_per_km = float(vehicle.fixed_per_km or 0)
        operating_per_km = float(vehicle.operating_per_km or 0)
        total_per_km = fixed_per_km + operating_per_km

        distance_km = request.distance_km

        # Calculate totals
        fixed_total = fixed_per_km * distance_km
        operating_total = operating_per_km * distance_km
        total_cost = total_per_km * distance_km

        # 5-Year projection (assuming 15,000 km/year)
        year_multipliers = [1.0, 1.08, 1.18, 1.30, 1.45]
        yearly_projection = [
            total_per_km * 15000 * multiplier 
            for multiplier in year_multipliers
        ]

        return CalculateResponse(
            total_cost=total_cost,
            per_km=total_per_km,
            fixed_per_km=fixed_per_km,
            operating_per_km=operating_per_km,
            fixed_total=fixed_total,
            operating_total=operating_total,
            yearly_projection=yearly_projection
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating costs: {str(e)}")
