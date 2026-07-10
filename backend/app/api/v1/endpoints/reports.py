from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timedelta
from app.core.database import supabase
from app.core.security import get_current_active_user

router = APIRouter()


@router.get("/reports/valuation-history")
async def get_valuation_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(get_current_active_user)
):
    """Generate valuation history report"""
    try:
        # Get all user's vehicles
        vehicles = (
            supabase
            .table("vehicles")
            .select("id, make, model, registration")
            .eq("user_id", current_user.id)
            .execute()
        )
        
        vehicle_ids = [v["id"] for v in vehicles.data]
        
        if not vehicle_ids:
            return {"vehicles": [], "summary": {"total_vehicles": 0}}
        
        # Get mileage entries for these vehicles
        query = (
            supabase
            .table("mileage_entries")
            .select("*, vehicles(*)")
            .in_("vehicle_id", vehicle_ids)
            .order("recorded_date", desc=True)
        )
        
        if start_date:
            query = query.gte("recorded_date", start_date)
        if end_date:
            query = query.lte("recorded_date", end_date)
            
        result = query.execute()
        
        return {
            "vehicles": vehicles.data,
            "mileage_entries": result.data,
            "summary": {
                "total_vehicles": len(vehicles.data),
                "total_entries": len(result.data),
                "generated_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/mileage-summary")
async def get_mileage_summary(
    current_user = Depends(get_current_active_user)
):
    """Get mileage summary for all user's vehicles"""
    try:
        vehicles = (
            supabase
            .table("vehicles")
            .select("id, make, model, registration, current_mileage")
            .eq("user_id", current_user.id)
            .execute()
        )
        
        # Get latest mileage entry for each vehicle
        summary = []
        for vehicle in vehicles.data:
            latest = (
                supabase
                .table("mileage_entries")
                .select("*")
                .eq("vehicle_id", vehicle["id"])
                .order("recorded_date", desc=True)
                .limit(1)
                .execute()
            )
            
            summary.append({
                "vehicle": vehicle,
                "latest_mileage": latest.data[0] if latest.data else None
            })
        
        return {
            "vehicles": summary,
            "total_vehicles": len(summary),
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/vehicle-details/{vehicle_id}")
async def get_vehicle_comprehensive_report(
    vehicle_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get comprehensive report for a single vehicle"""
    try:
        # Get vehicle details
        vehicle = (
            supabase
            .table("vehicles")
            .select("*")
            .eq("id", vehicle_id)
            .execute()
        )
        
        if not vehicle.data:
            raise HTTPException(status_code=404, detail="Vehicle not found")
            
        if vehicle.data[0]["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Get mileage history
        mileage = (
            supabase
            .table("mileage_entries")
            .select("*")
            .eq("vehicle_id", vehicle_id)
            .order("recorded_date", desc=True)
            .execute()
        )
        
        # Get inspections
        inspections = (
            supabase
            .table("inspections")
            .select("*")
            .eq("vehicle_id", vehicle_id)
            .order("inspection_date", desc=True)
            .execute()
        )
        
        return {
            "vehicle": vehicle.data[0],
            "mileage_history": mileage.data,
            "inspections": inspections.data,
            "summary": {
                "total_mileage_entries": len(mileage.data),
                "total_inspections": len(inspections.data),
                "average_mileage": sum([m["current_mileage"] for m in mileage.data]) / len(mileage.data) if mileage.data else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
