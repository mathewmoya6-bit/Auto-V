from typing import List, Optional, Dict, Any
from uuid import UUID
from app.core.database import supabase


class InstantValueService:
    """Service for handling instant value operations"""
    
    async def save_valuation_history(
        self, 
        user_id: UUID, 
        vehicle_data: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save instant valuation to history"""
        history_record = {
            "user_id": str(user_id),
            "make": vehicle_data.get("make"),
            "model": vehicle_data.get("model"),
            "year": vehicle_data.get("year"),
            "mileage": vehicle_data.get("mileage", 0),
            "condition": vehicle_data.get("condition", "Good"),
            "location": vehicle_data.get("location", "Other"),
            "market_value": result["market_value"],
            "confidence_score": result["confidence_score"],
            "certificate_number": result["certificate_number"],
            "factors": result["factors"],
            "vehicle_details": result["vehicle_details"]
        }
        
        response = (
            supabase
            .table("instant_valuations")
            .insert(history_record)
            .execute()
        )
        
        return response.data[0] if response.data else {}
    
    async def get_history(
        self, 
        user_id: UUID, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's instant valuation history"""
        response = (
            supabase
            .table("instant_valuations")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data
    
    async def get_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get user's instant valuation statistics"""
        response = (
            supabase
            .table("instant_valuations")
            .select("market_value, confidence_score")
            .eq("user_id", str(user_id))
            .execute()
        )
        
        data = response.data
        if not data:
            return {
                "total_valuations": 0,
                "average_value": 0,
                "average_confidence": 0,
                "highest_value": 0,
                "lowest_value": 0
            }
        
        values = [v.get("market_value", 0) for v in data]
        confidences = [v.get("confidence_score", 0) for v in data]
        
        return {
            "total_valuations": len(data),
            "average_value": round(sum(values) / len(values), 2),
            "average_confidence": round(sum(confidences) / len(confidences), 2),
            "highest_value": max(values),
            "lowest_value": min(values)
        }
