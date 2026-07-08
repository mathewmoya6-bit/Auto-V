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


# ─── IMPORTANT: /models must be declared BEFORE /{vehicle_id} ──────────
# Otherwise a request to /vehicles/models gets matched as
# GET /vehicles/{vehicle_id} with vehicle_id="models" instead.

@router.get("/models")
async def get_vehicle_models():
    """
    Return the list of known make/model pairs for populating the
    Instant Value Check dropdown.

    NOTE: this is a placeholder dataset. Replace with a real query once
    there's a proper vehicle catalog table/service backing this.
    """
    catalog = [
        {"make": "Toyota", "model": "Corolla"},
        {"make": "Toyota", "model": "Axio"},
        {"make": "Toyota", "model": "Camry"},
        {"make": "Toyota", "model": "RAV4"},
        {"make": "Toyota", "model": "Hilux"},
        {"make": "Toyota", "model": "Land Cruiser"},
        {"make": "Honda", "model": "Civic"},
        {"make": "Honda", "model": "Accord"},
        {"make": "Honda", "model": "CR-V"},
        {"make": "Honda", "model": "Fit"},
        {"make": "Nissan", "model": "X-Trail"},
        {"make": "Nissan", "model": "Patrol"},
        {"make": "Nissan", "model": "Note"},
        {"make": "Nissan", "model": "Qashqai"},
        {"make": "BMW", "model": "X5"},
        {"make": "BMW", "model": "3 Series"},
        {"make": "BMW", "model": "5 Series"},
        {"make": "BMW", "model": "7 Series"},
        {"make": "Mercedes", "model": "C-Class"},
        {"make": "Mercedes", "model": "E-Class"},
        {"make": "Mercedes", "model": "GLC"},
        {"make": "Mercedes", "model": "GLE"},
    ]
    return catalog


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
