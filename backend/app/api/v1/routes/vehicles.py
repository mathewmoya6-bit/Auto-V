# app/api/v1/routes/vehicles.py
# =============================================================================
# AUTO-V API - Vehicle Routes
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List

from app.services.vehicle_service import VehicleService
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
)

router = APIRouter(tags=["Vehicles"])
service = VehicleService()


@router.get("/", response_model=List[VehicleResponse])
async def get_vehicles(user_id: Optional[str] = Query(None)):
    """Get all vehicles."""
    try:
        return service.get_vehicles(user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(vehicle_id: str):
    """Get a single vehicle by ID."""
    try:
        vehicle = service.get_vehicle(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
        return vehicle
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(data: VehicleCreate):
    """Create a new vehicle."""
    try:
        return service.create_vehicle(data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(vehicle_id: str, data: VehicleUpdate):
    """Update a vehicle."""
    try:
        vehicle = service.update_vehicle(vehicle_id, data)
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
        return vehicle
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(vehicle_id: str):
    """Delete a vehicle."""
    try:
        deleted = service.delete_vehicle(vehicle_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


__all__ = ["router"]
