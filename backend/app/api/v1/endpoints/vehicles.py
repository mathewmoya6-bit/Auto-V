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
    """Get all vehicle makes and models for dropdowns"""
    try:
        result = (
            supabase
            .table("vehicles")
            .select("make, model")
            .execute()
        )
        
        # Build unique make-model pairs
        models = []
        seen = set()
        for item in result.data:
            key = f"{item['make']}|{item['model']}"
            if key not in seen:
                seen.add(key)
                models.append({
                    "make": item["make"],
                    "model": item["model"]
                })
        
        return models
    except Exception as e:
        # Return fallback data if table doesn't exist
        return [
            {"make": "Toyota", "model": "Corolla"},
            {"make": "Toyota", "model": "Camry"},
            {"make": "Honda", "model": "Civic"},
            {"make": "Nissan", "model": "X-Trail"},
            {"make": "BMW", "model": "X5"},
            {"make": "Mercedes", "model": "C-Class"}
        ]


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
