from fastapi import APIRouter, HTTPException, Depends
from app.services.valuation_service import ValuationService
from app.schemas.valuation import ValuationRequest, ValuationResponse
from app.core.security import get_current_active_user

router = APIRouter()
valuation_service = ValuationService()


@router.post("/valuation/calculate", response_model=ValuationResponse)
async def calculate_valuation(
    request: ValuationRequest,
    current_user = Depends(get_current_active_user)
):
    """Calculate vehicle valuation based on various factors"""
    try:
        valuation = await valuation_service.calculate_valuation(request)
        return valuation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vehicles/{vehicle_id}/valuation")
async def get_vehicle_valuation(
    vehicle_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get current valuation for a specific vehicle"""
    try:
        valuation = await valuation_service.get_vehicle_valuation(vehicle_id)
        if not valuation:
            raise HTTPException(status_code=404, detail="Valuation not found")
        return valuation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/valuation/history/{vehicle_id}")
async def get_valuation_history(
    vehicle_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get valuation history for a vehicle"""
    try:
        history = await valuation_service.get_valuation_history(vehicle_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
