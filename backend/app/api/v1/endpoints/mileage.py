from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.core.database import supabase, admin
from app.schemas.mileage import MileageEntryCreate, MileageEntryResponse
from app.services.mileage_service import MileageService
from app.core.security import get_current_active_user

router = APIRouter()
mileage_service = MileageService()


@router.get("/vehicles/{vehicle_id}/mileage", response_model=List[MileageEntryResponse])
async def get_vehicle_mileage(
    vehicle_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get mileage history for a vehicle"""
    try:
        # Verify vehicle ownership
        vehicle = (
            supabase
            .table("vehicles")
            .select("user_id")
            .eq("id", vehicle_id)
            .execute()
        )
        
        if not vehicle.data:
            raise HTTPException(status_code=404, detail="Vehicle not found")
            
        if vehicle.data[0]["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        result = (
            supabase
            .table("mileage_entries")
            .select("*")
            .eq("vehicle_id", vehicle_id)
            .order("recorded_date", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vehicles/{vehicle_id}/mileage", response_model=MileageEntryResponse)
async def add_mileage_entry(
    vehicle_id: str,
    entry: MileageEntryCreate,
    current_user = Depends(get_current_active_user)
):
    """Add a mileage entry for a vehicle"""
    try:
        # Verify vehicle ownership
        vehicle = (
            supabase
            .table("vehicles")
            .select("user_id, current_mileage")
            .eq("id", vehicle_id)
            .execute()
        )
        
        if not vehicle.data:
            raise HTTPException(status_code=404, detail="Vehicle not found")
            
        if vehicle.data[0]["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Validate mileage entry
        current_mileage = vehicle.data[0].get("current_mileage", 0)
        if entry.current_mileage <= current_mileage:
            raise HTTPException(
                status_code=400, 
                detail=f"Current mileage must be greater than previous ({current_mileage})"
            )
        
        entry_data = entry.model_dump()
        entry_data["vehicle_id"] = vehicle_id
        entry_data["previous_mileage"] = current_mileage
        
        # Insert mileage entry
        result = (
            admin
            .table("mileage_entries")
            .insert(entry_data)
            .execute()
        )
        
        # Update vehicle's current mileage
        (
            admin
            .table("vehicles")
            .update({"current_mileage": entry.current_mileage})
            .eq("id", vehicle_id)
            .execute()
        )
        
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest", response_model=List[MileageEntryResponse])
async def get_latest_mileage_entries(
    limit: int = 10,
    current_user = Depends(get_current_active_user)
):
    """Get latest mileage entries across all user's vehicles"""
    try:
        # Get all user's vehicles
        vehicles = (
            supabase
            .table("vehicles")
            .select("id")
            .eq("user_id", current_user.id)
            .execute()
        )
        
        vehicle_ids = [v["id"] for v in vehicles.data]
        
        if not vehicle_ids:
            return []
        
        result = (
            supabase
            .table("mileage_entries")
            .select("*, vehicles(*)")
            .in_("vehicle_id", vehicle_ids)
            .order("recorded_date", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
