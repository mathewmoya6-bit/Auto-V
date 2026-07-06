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
        estimated_value=450000,
        value_range_low=425000,
        value_range_high=475000,
        confidence_score=87.5,
        property_address={
            "street": request.address.street,
            "city": request.address.city,
            "state": request.address.state,
            "zip_code": request.address.zip_code
        },
        property_type=request.property_type,
        square_feet=request.features.square_feet,
        bedrooms=request.features.bedrooms,
        bathrooms=request.features.bathrooms,
        data_source=["automated"]
    )
