from typing import List, Optional, Dict, Any
from uuid import UUID
from app.core.database import supabase


class VehicleAssessmentService:
    """Service for handling vehicle assessment operations"""
    
    async def save_assessment(
        self,
        user_id: UUID,
        assessment_data: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save vehicle assessment to history"""
        record = {
            "user_id": str(user_id),
            "make": assessment_data.get("make"),
            "model": assessment_data.get("model"),
            "year": assessment_data.get("year"),
            "mileage": assessment_data.get("mileage", 0),
            "condition": assessment_data.get("condition", "Good"),
            "location": assessment_data.get("location", "Other"),
            "market_value": result["market_value"],
            "condition_score": result["condition_assessment"]["score"],
            "condition_rating": result["condition_assessment"]["overall_rating"],
            "maintenance_cost": result["maintenance_cost"],
            "investment_rating": result["investment_recommendation"]["rating"],
            "assessment_data": result
        }
        
        response = (
            supabase
            .table("vehicle_assessments")
            .insert(record)
            .execute()
        )
        
        return response.data[0] if response.data else {}
    
    async def get_history(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's assessment history"""
        response = (
            supabase
            .table("vehicle_assessments")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data
    
    async def get_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get user's assessment statistics"""
        response = (
            supabase
            .table("vehicle_assessments")
            .select("market_value, condition_score, maintenance_cost, investment_rating")
            .eq("user_id", str(user_id))
            .execute()
        )
        
        data = response.data
        if not data:
            return {
                "total_assessments": 0,
                "average_value": 0,
                "average_condition_score": 0,
                "average_maintenance_cost": 0,
                "highest_value": 0,
                "lowest_value": 0,
                "investment_ratings": {
                    "Strong Buy": 0,
                    "Buy": 0,
                    "Hold": 0,
                    "Caution": 0,
                    "Avoid": 0
                }
            }
        
        values = [v.get("market_value", 0) for v in data]
        condition_scores = [v.get("condition_score", 0) for v in data]
        maintenance_costs = [v.get("maintenance_cost", 0) for v in data]
        
        investment_ratings = {"Strong Buy": 0, "Buy": 0, "Hold": 0, "Caution": 0, "Avoid": 0}
        for v in data:
            rating = v.get("investment_rating")
            if rating in investment_ratings:
                investment_ratings[rating] += 1
        
        return {
            "total_assessments": len(data),
            "average_value": round(sum(values) / len(values), 2) if values else 0,
            "average_condition_score": round(sum(condition_scores) / len(condition_scores), 2) if condition_scores else 0,
            "average_maintenance_cost": round(sum(maintenance_costs) / len(maintenance_costs), 2) if maintenance_costs else 0,
            "highest_value": max(values) if values else 0,
            "lowest_value": min(values) if values else 0,
            "investment_ratings": investment_ratings
        }
