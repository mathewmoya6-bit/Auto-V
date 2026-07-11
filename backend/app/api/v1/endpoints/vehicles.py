from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from app.core.database import supabase, admin
from app.schemas.vehicles import (
    VehicleCreate, 
    VehicleUpdate, 
    VehicleResponse,
    VehicleDetailResponse
)
from app.core.security import get_current_user, get_current_active_user

router = APIRouter()


@router.get("/models")
async def list_vehicle_models():
    """
    Get all known vehicle makes and models for dropdowns/autocomplete.

    Pulled from two sources and merged:
    - `vehicles`: user-registered vehicle records (Vehicles module)
    - `valuations`: every completed Instant Value / Valuation submission

    The `vehicles` table alone is not a reliable source here — most people
    using Instant Value never register a Vehicle record at all, they only
    ever create rows in `valuations`. Without also reading `valuations`,
    this endpoint would stay empty indefinitely for real users.
    """
    seen = set()
    models: list[dict] = []

    def _add_from(rows):
        for item in rows:
            make = (item.get("make") or "").strip()
            model = (item.get("model") or "").strip()
            if not make or not model:
                continue
            key = f"{make}|{model}"
            if key not in seen:
                seen.add(key)
                models.append({"make": make, "model": model})

    try:
        vehicles_result = supabase.table("vehicles").select("make, model").execute()
        _add_from(vehicles_result.data or [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch vehicle models: {e}")

    try:
        valuations_result = supabase.table("valuations").select("make, model").execute()
        _add_from(valuations_result.data or [])
    except Exception as e:
        # Don't fail the whole request if only this second source has an
        # issue (e.g. table not migrated yet on an older deployment) - the
        # vehicles-table data above is still valid and useful on its own.
        pass

    return models


@router.get("/", response_model=List[VehicleResponse])
async def get_my_vehicles(
    current_user = Depends(get_current_active_user),
    status: Optional[str] = None
):
    """Get all vehicles for the current user"""
    try:
        query = (
            supabase
            .table("vehicles")
            .select("*")
            .eq("user_id", current_user.id)
        )
        
        if status:
            query = query.eq("status", status)
            
        result = query.order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=VehicleResponse)
async def create_vehicle(
    vehicle: VehicleCreate,
    current_user = Depends(get_current_active_user)
):
    """Create a new vehicle"""
    try:
        vehicle_data = vehicle.model_dump()
        vehicle_data["user_id"] = current_user.id
        
        result = (
            admin
            .table("vehicles")
            .insert(vehicle_data)
            .execute()
        )
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vehicle_id}", response_model=VehicleDetailResponse)
async def get_vehicle(
    vehicle_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get vehicle by ID"""
    try:
        result = (
            supabase
            .table("vehicles")
            .select("*, vehicle_categories(*)")
            .eq("id", vehicle_id)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Vehicle not found")
            
        vehicle = result.data[0]
        
        # Check if user owns this vehicle or is admin
        if vehicle["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this vehicle")
            
        return vehicle
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: str,
    vehicle_update: VehicleUpdate,
    current_user = Depends(get_current_active_user)
):
    """Update vehicle details"""
    try:
        # First check if vehicle exists and belongs to user
        check = (
            supabase
            .table("vehicles")
            .select("user_id")
            .eq("id", vehicle_id)
            .execute()
        )
        
        if not check.data:
            raise HTTPException(status_code=404, detail="Vehicle not found")
            
        if check.data[0]["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this vehicle")
        
        result = (
            admin
            .table("vehicles")
            .update(vehicle_update.model_dump(exclude_unset=True))
            .eq("id", vehicle_id)
            .execute()
        )
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: str,
    current_user = Depends(get_current_active_user)
):
    """Delete a vehicle"""
    try:
        # Check ownership
        check = (
            supabase
            .table("vehicles")
            .select("user_id")
            .eq("id", vehicle_id)
            .execute()
        )
        
        if not check.data:
            raise HTTPException(status_code=404, detail="Vehicle not found")
            
        if check.data[0]["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this vehicle")
        
        result = (
            admin
            .table("vehicles")
            .delete()
            .eq("id", vehicle_id)
            .execute()
        )
        return {"message": "Vehicle deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
