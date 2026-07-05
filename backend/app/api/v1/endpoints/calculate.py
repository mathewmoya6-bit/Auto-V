# backend/app/api/v1/endpoints/calculate.py
# =============================================================================
# Mileage Calculation Endpoint - Business Logic
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from app.core.database import get_db
from app.models.vehicle_variant import VehicleVariant
from app.models.vehicle_category import VehicleCategory

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class MileageRequest(BaseModel):
    """Request model for mileage calculation."""
    variant_id: str = Field(..., description="UUID of the vehicle variant")
    distance: float = Field(..., gt=0, description="Distance in kilometers")
    include_forecast: Optional[bool] = Field(False, description="Include 5-year forecast")
    include_comparison: Optional[bool] = Field(False, description="Include fuel type comparison")


class MileageResponse(BaseModel):
    """Response model for mileage calculation."""
    totalCost: float
    fixedCost: float
    operatingCost: float
    totalRate: float
    fixedRate: float
    operatingRate: float
    components: Dict[str, float] = {}
    yearly: Dict[str, float] = {}
    initialCost: float
    method: str
    distance: float
    forecast: Optional[Dict[str, float]] = None
    comparison: Optional[Dict[str, Any]] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/calculate/mileage", response_model=MileageResponse)
async def calculate_mileage(
    request: MileageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate mileage costs for a vehicle variant.
    
    Business Logic:
    1. Fetch variant from database
    2. Calculate fixed and operating costs
    3. Provide detailed breakdowns
    4. Generate forecasts (optional)
    5. Fuel type comparisons (optional)
    """
    try:
        # 1. Fetch variant from database with category
        query = (
            select(VehicleVariant, VehicleCategory)
            .join(
                VehicleCategory,
                VehicleVariant.category_id == VehicleCategory.id
            )
            .where(VehicleVariant.id == request.variant_id)
            .where(VehicleVariant.is_active == True)
        )
        
        result = await db.execute(query)
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Variant with ID {request.variant_id} not found"
            )
        
        variant, category = row
        
        # 2. Calculate costs
        fixed_rate = float(variant.fixed_per_km or 0)
        operating_rate = float(variant.operating_per_km or 0)
        total_rate = float(variant.total_per_km or (fixed_rate + operating_rate))
        
        total_cost = total_rate * request.distance
        fixed_cost = fixed_rate * request.distance
        operating_cost = operating_rate * request.distance
        
        # 3. Component breakdown
        components = variant.components or {}
        component_costs = {}
        for key, value in components.items():
            try:
                component_costs[key] = float(value or 0) * request.distance
            except (ValueError, TypeError):
                component_costs[key] = 0
        
        # 4. Build response
        response_data = {
            "totalCost": round(total_cost, 2),
            "fixedCost": round(fixed_cost, 2),
            "operatingCost": round(operating_cost, 2),
            "totalRate": round(total_rate, 4),
            "fixedRate": round(fixed_rate, 4),
            "operatingRate": round(operating_rate, 4),
            "components": component_costs,
            "yearly": {
                "year1": float(variant.year1 or 0),
                "year2": float(variant.year2 or 0),
                "year3": float(variant.year3 or 0),
                "year4": float(variant.year4 or 0),
                "year5": float(variant.year5 or 0)
            },
            "initialCost": float(variant.initial_cost or 0),
            "method": "fastapi",
            "distance": request.distance
        }
        
        # 5. Add forecast if requested
        if request.include_forecast:
            response_data["forecast"] = calculate_forecast(variant, request.distance)
        
        # 6. Add comparison if requested
        if request.include_comparison and category:
            response_data["comparison"] = get_comparison(variant, category)
        
        logger.info(f"✅ Mileage calculation completed for variant: {variant.label}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calculate/health")
async def calculate_health():
    """Health check for calculation service."""
    return {
        "status": "healthy",
        "service": "calculation",
        "version": "1.0.0"
    }


def calculate_forecast(variant, distance: float) -> Dict[str, float]:
    """Calculate 5-year forecast."""
    forecast = {}
    yearly_rates = {
        'year1': float(variant.year1 or 0),
        'year2': float(variant.year2 or 0),
        'year3': float(variant.year3 or 0),
        'year4': float(variant.year4 or 0),
        'year5': float(variant.year5 or 0)
    }
    
    total_rate = float(variant.total_per_km or (float(variant.fixed_per_km or 0) + float(variant.operating_per_km or 0)))
    
    for year, rate in yearly_rates.items():
        if rate > 0:
            forecast[year] = round(rate * distance, 2)
        else:
            # If no specific rate, use base rate with slight increase
            adjustment = {'year1': 1.00, 'year2': 1.02, 'year3': 1.04, 'year4': 1.06, 'year5': 1.08}
            forecast[year] = round(total_rate * distance * adjustment.get(year, 1.0), 2)
    
    return forecast


def get_comparison(variant, category) -> Dict[str, Any]:
    """Get fuel type comparison data."""
    fuel_type = category.fuel_type or 'Unknown'
    
    # Average rates by fuel type (based on Kenya data)
    averages = {
        'Petrol': 45.00,
        'Diesel': 52.00,
        'Electric': 30.00,
        'LPG': 38.00,
        'Unknown': 45.00
    }
    
    current_rate = float(variant.total_per_km or 0)
    
    return {
        "fuelType": fuel_type,
        "category": category.name,
        "currentRate": round(current_rate, 4),
        "averageRate": averages.get(fuel_type, 45.00),
        "difference": round(current_rate - averages.get(fuel_type, 45.00), 4),
        "isBelowAverage": current_rate < averages.get(fuel_type, 45.00)
    }
