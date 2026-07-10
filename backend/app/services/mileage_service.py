from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.core.database import supabase


class MileageService:
    async def get_mileage_trends(self, vehicle_id: str, days: int = 30) -> Dict[str, Any]:
        """Get mileage trends for a vehicle"""
        start_date = datetime.now() - timedelta(days=days)
        
        entries = (
            supabase
            .table("mileage_entries")
            .select("*")
            .eq("vehicle_id", vehicle_id)
            .gte("recorded_date", start_date.isoformat())
            .order("recorded_date", asc=True)
            .execute()
        )
        
        if not entries.data:
            return {"trend": "insufficient_data", "daily_average": 0}
        
        # Calculate daily average
        if len(entries.data) > 1:
            first_entry = entries.data[0]
            last_entry = entries.data[-1]
            days_between = (datetime.fromisoformat(last_entry["recorded_date"]) - 
                          datetime.fromisoformat(first_entry["recorded_date"])).days
            
            if days_between > 0:
                daily_average = (last_entry["current_mileage"] - first_entry["current_mileage"]) / days_between
            else:
                daily_average = 0
        else:
            daily_average = 0
        
        # Determine trend
        if daily_average > 50:
            trend = "high_usage"
        elif daily_average > 20:
            trend = "moderate_usage"
        elif daily_average > 0:
            trend = "low_usage"
        else:
            trend = "no_usage"
        
        return {
            "trend": trend,
            "daily_average": round(daily_average, 2),
            "total_mileage": entries.data[-1]["current_mileage"] - entries.data[0]["current_mileage"] if len(entries.data) > 1 else 0,
            "entries_count": len(entries.data),
            "period_days": days
        }
    
    async def validate_mileage_entry(self, vehicle_id: str, current_mileage: float) -> bool:
        """Validate a mileage entry"""
        # Get current mileage
        vehicle = (
            supabase
            .table("vehicles")
            .select("current_mileage")
            .eq("id", vehicle_id)
            .execute()
        )
        
        if not vehicle.data:
            return False
        
        previous_mileage = vehicle.data[0].get("current_mileage", 0)
        
        # Mileage must be greater than previous
        if current_mileage <= previous_mileage:
            return False
        
        # Mileage shouldn't increase by more than 1000km per day (unrealistic)
        max_daily_increase = 1000
        
        # Check last entry date
        last_entry = (
            supabase
            .table("mileage_entries")
            .select("recorded_date")
            .eq("vehicle_id", vehicle_id)
            .order("recorded_date", desc=True)
            .limit(1)
            .execute()
        )
        
        if last_entry.data:
            last_date = datetime.fromisoformat(last_entry.data[0]["recorded_date"])
            days_diff = (datetime.now() - last_date).days
            max_allowed = previous_mileage + (max_daily_increase * max(days_diff, 1))
            
            if current_mileage > max_allowed:
                return False
        
        return True
