from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas import (
    ValuationRequest,
    ValuationResponse,
    InstantValueRequest,
    InstantValueResponse
)

router = APIRouter()

@router.post("/valuations", response_model=ValuationResponse)
async def create_valuation(request: ValuationRequest):
    """
    Create a detailed property valuation
    """
    # Your valuation logic here
    return ValuationResponse(
        property_id=request.property_id,
        estimated_value=450000,
        estimated_value_range_low=425000,
        estimated_value_range_high=475000,
        confidence_score=87.5,
        valuation_method=request.valuation_method
    )

@router.post("/instant-value", response_model=InstantValueResponse)
async def get_instant_value(request: InstantValueRequest):
    """
    Get an instant property value estimate
    """
    # Your instant value logic here
    return InstantValueResponse(
        property_id=request.property_id,
        instant_value=450000,
        value_range={"min": 425000, "max": 475000},
        confidence_level=87.5,
        estimated_at=datetime.now(),
        price_per_sqft=250,
        vs_zip_median=1.05,
        vs_city_median=0.92,
        market_trend="up",
        data_source="Automated Valuation Model"
    )
