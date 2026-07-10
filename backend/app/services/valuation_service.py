from typing import Optional, Dict, Any
from datetime import datetime
from app.core.database import supabase


class ValuationService:
    def __init__(self):
        self.valuation_factors = {
            "base_rate": 1000,  # Base rate per year
            "depreciation_rate": 0.15,  # 15% depreciation per year
            "mileage_factor": 0.01,  # 1% reduction per 1000km
            "condition_factors": {
                "excellent": 1.2,
                "good": 1.0,
                "fair": 0.8,
                "poor": 0.6
            }
        }
    
    async def calculate_valuation(self, request) -> Dict[str, Any]:
        """Calculate vehicle valuation"""
        # Get category base rate
        category = (
            supabase
            .table("vehicle_categories")
            .select("base_rate")
            .eq("id", request.category_id)
            .execute()
        )
        
        if not category.data:
            raise ValueError("Category not found")
        
        base_rate = category.data[0]["base_rate"]
        
        # Calculate age depreciation
        current_year = datetime.now().year
        age = current_year - request.year
        depreciation = 1 - (self.valuation_factors["depreciation_rate"] * age)
        depreciation = max(depreciation, 0.2)  # Minimum 20% of value
        
        # Mileage adjustment
        mileage_adjustment = 1 - ((request.mileage / 1000) * self.valuation_factors["mileage_factor"])
        mileage_adjustment = max(mileage_adjustment, 0.3)  # Maximum 70% reduction
        
        # Condition factor
        condition_factor = self.valuation_factors["condition_factors"].get(
            request.condition, 
            1.0
        )
        
        # Calculate final value
        base_value = base_rate * depreciation
        adjusted_value = base_value * mileage_adjustment * condition_factor
        
        # Apply optional extras
        extras_value = sum(request.extras) if hasattr(request, 'extras') else 0
        
        final_value = adjusted_value + extras_value
        
        return {
            "vehicle_id": request.vehicle_id if hasattr(request, 'vehicle_id') else None,
            "base_value": round(base_value, 2),
            "adjusted_value": round(adjusted_value, 2),
            "final_value": round(final_value, 2),
            "factors": {
                "age": age,
                "depreciation_rate": self.valuation_factors["depreciation_rate"],
                "mileage": request.mileage,
                "condition": request.condition,
                "condition_factor": condition_factor
            },
            "calculated_at": datetime.now().isoformat()
        }
    
    async def get_vehicle_valuation(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Get current valuation for a vehicle"""
        # Get vehicle details
        vehicle = (
            supabase
            .table("vehicles")
            .select("*")
            .eq("id", vehicle_id)
            .execute()
        )
        
        if not vehicle.data:
            return None
        
        vehicle_data = vehicle.data[0]
        
        # Create valuation request
        request = type('Request', (), {
            'category_id': vehicle_data.get("category_id"),
            'year': vehicle_data.get("year"),
            'mileage': vehicle_data.get("current_mileage", 0),
            'condition': vehicle_data.get("condition", "good"),
            'vehicle_id': vehicle_id,
            'extras': []
        })()
        
        return await self.calculate_valuation(request)
    
    async def get_valuation_history(self, vehicle_id: str) -> list:
        """Get valuation history for a vehicle"""
        # Get mileage history
        entries = (
            supabase
            .table("mileage_entries")
            .select("*")
            .eq("vehicle_id", vehicle_id)
            .order("recorded_date", asc=True)
            .execute()
        )
        
        history = []
        for entry in entries.data:
            # Calculate valuation at each mileage point
            request = type('Request', (), {
                'category_id': None,  # Would need to fetch from vehicle
                'year': 2020,  # Would need from vehicle
                'mileage': entry["current_mileage"],
                'condition': "good",  # Would need from vehicle
                'vehicle_id': vehicle_id,
                'extras': []
            })()
            valuation = await self.calculate_valuation(request)
            history.append({
                "date": entry["recorded_date"],
                "mileage": entry["current_mileage"],
                "value": valuation["final_value"]
            })
        
        return history
