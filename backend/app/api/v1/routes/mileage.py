# app/api/v1/routes/mileage.py
# =============================================================================
# Mileage Routes - Vehicle Categories, Variants, and Cost Calculation
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.mileage import VehicleCategory, VehicleVariant

router = APIRouter()

# ─── Pydantic Models for Responses ─────────────────────────────────

class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class VehicleVariantResponse(BaseModel):
    id: str
    category_id: str
    name: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    engine_size: Optional[str] = None
    fuel_type: Optional[str] = None
    initial_cost: Optional[float] = None
    insurance_rate: Optional[float] = None
    depreciation_rate: Optional[float] = None
    interest_rate: Optional[float] = None
    fuel_rate: Optional[float] = None
    servicing_rate: Optional[float] = None
    repairs_rate: Optional[float] = None
    tyres_rate: Optional[float] = None
    licences_rate: Optional[float] = None
    is_primary: Optional[bool] = False

    class Config:
        from_attributes = True

class CalculateRequest(BaseModel):
    vehicle_id: str
    distance_km: float

class CostBreakdown(BaseModel):
    Insurance: float
    Depreciation: float
    Interest: float
    Fuel: float
    Servicing: float
    Repairs: float
    Tyres: float
    Licences: float

class CalculateResponse(BaseModel):
    total_cost: float
    per_km: float
    fixed_per_km: float
    operating_per_km: float
    fixed_total: float
    operating_total: float
    breakdown: CostBreakdown
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
            select(VehicleCategory).order_by(VehicleCategory.name)
        )
        categories = result.scalars().all()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")

@router.get("/vehicles", response_model=List[VehicleVariantResponse])
async def get_vehicles(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    fuel_type: Optional[str] = Query(None, description="Filter by fuel type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all vehicle variants with optional filters
    """
    try:
        query = select(VehicleVariant)
        
        if category_id:
            query = query.where(VehicleVariant.category_id == category_id)
        if fuel_type:
            query = query.where(VehicleVariant.fuel_type == fuel_type)
            
        query = query.order_by(VehicleVariant.make, VehicleVariant.model)
        
        result = await db.execute(query)
        vehicles = result.scalars().all()
        return vehicles
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
        
        # Extract rates (default to 0 if not present)
        insurance = vehicle.insurance_rate or 0.0
        depreciation = vehicle.depreciation_rate or 0.0
        interest = vehicle.interest_rate or 0.0
        fuel = vehicle.fuel_rate or 0.0
        servicing = vehicle.servicing_rate or 0.0
        repairs = vehicle.repairs_rate or 0.0
        tyres = vehicle.tyres_rate or 0.0
        licences = vehicle.licences_rate or 0.0

        # Calculate per-km costs
        fixed_per_km = insurance + depreciation + interest + licences
        operating_per_km = fuel + servicing + repairs + tyres
        total_per_km = fixed_per_km + operating_per_km

        distance_km = request.distance_km

        # Calculate total costs for the trip
        fixed_total = fixed_per_km * distance_km
        operating_total = operating_per_km * distance_km
        total_cost = total_per_km * distance_km

        # Create breakdown
        breakdown = CostBreakdown(
            Insurance=insurance,
            Depreciation=depreciation,
            Interest=interest,
            Fuel=fuel,
            Servicing=servicing,
            Repairs=repairs,
            Tyres=tyres,
            Licences=licences
        )

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
            breakdown=breakdown,
            yearly_projection=yearly_projection
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating costs: {str(e)}")
