from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.core.database import supabase, admin
from app.schemas.inspections import (
    InspectionCreate,
    InspectionUpdate,
    InspectionResponse,
    InspectionReport
)
from app.core.security import get_current_active_user

router = APIRouter()


@router.get("/vehicles/{vehicle_id}/inspections", response_model=List[InspectionResponse])
async def get_vehicle_inspections(
    vehicle_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get all inspections for a vehicle"""
    try:
        # Verify ownership
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
            .table("inspections")
            .select("*")
            .eq("vehicle_id", vehicle_id)
            .order("inspection_date", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vehicles/{vehicle_id}/inspections", response_model=InspectionResponse)
async def create_inspection(
    vehicle_id: str,
    inspection: InspectionCreate,
    current_user = Depends(get_current_active_user)
):
    """Create a new inspection record"""
    try:
        # Verify ownership
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
        
        inspection_data = inspection.model_dump()
        inspection_data["vehicle_id"] = vehicle_id
        inspection_data["inspector_id"] = current_user.id
        
        result = (
            admin
            .table("inspections")
            .insert(inspection_data)
            .execute()
        )
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inspections/{inspection_id}", response_model=InspectionReport)
async def get_inspection_report(
    inspection_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get detailed inspection report"""
    try:
        result = (
            supabase
            .table("inspections")
            .select("*, vehicles(*)")
            .eq("id", inspection_id)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Inspection not found")
            
        inspection = result.data[0]
        
        # Verify ownership
        if inspection["vehicles"]["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        return inspection
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
