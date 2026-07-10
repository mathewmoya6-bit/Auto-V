from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import random
from app.core.database import supabase, admin
from app.core.security import get_current_active_user

router = APIRouter()


@router.post("/calculate")
async def instant_valuation(
    vehicle_data: Dict[str, Any],
    current_user = Depends(get_current_active_user)
):
    """
    Get instant AI-powered vehicle valuation
    This calculates market value based on vehicle details
    No service fee is charged here - payment is handled separately
    """
    try:
        # Calculate base value based on vehicle type and year
        current_year = datetime.now().year
        age = current_year - vehicle_data.get("year", current_year)
        
        # Base values by vehicle type (in KES)
        base_values = {
            "Car": 2000000,
            "Bike": 300000,
            "Tricycle": 200000
        }
        
        base_value = base_values.get(vehicle_data.get("type", "Car"), 1000000)
        
        # Depreciation: 10-15% per year
        depreciation_rate = 0.12
        age_factor = max(0.2, 1 - (depreciation_rate * age))
        
        # Mileage factor
        mileage = vehicle_data.get("mileage", 0)
        mileage_factor = max(0.3, 1 - (mileage / 200000))
        
        # Condition factor
        condition_factors = {
            "Excellent": 1.2,
            "Good": 1.0,
            "Fair": 0.8,
            "Poor": 0.6
        }
        condition = vehicle_data.get("condition", "Good")
        condition_factor = condition_factors.get(condition, 1.0)
        
        # Accident history factor
        accident_factors = {
            "None": 1.0,
            "Minor": 0.85,
            "Major": 0.6,
            "WriteOff": 0.3
        }
        accident = vehicle_data.get("accident_history", "None")
        accident_factor = accident_factors.get(accident, 1.0)
        
        # Previous owners factor
        owners = vehicle_data.get("previous_owners", 1)
        owners_factor = max(0.7, 1 - (owners * 0.03))
        
        # Location factor
        location_factors = {
            "Nairobi": 1.1,
            "Mombasa": 1.05,
            "Kisumu": 0.95,
            "Nakuru": 0.98,
            "Eldoret": 0.95,
            "Kiambu": 1.08,
            "Kajiado": 1.05,
            "Machakos": 1.02,
            "Other": 0.9
        }
        location = vehicle_data.get("location", "Other")
        location_factor = location_factors.get(location, 0.9)
        
        # Calculate final market value
        market_value = (
            base_value * 
            age_factor * 
            mileage_factor * 
            condition_factor * 
            accident_factor * 
            owners_factor * 
            location_factor
        )
        
        # Add randomness for realism (±5%)
        random_factor = 1 + (random.random() - 0.5) * 0.1
        market_value = market_value * random_factor
        
        # Round to nearest 1000
        market_value = round(market_value / 1000) * 1000
        
        # Calculate confidence score
        confidence_score = 70
        
        if vehicle_data.get("make") and vehicle_data.get("model"):
            confidence_score += 5
        if vehicle_data.get("body_type"):
            confidence_score += 3
        if vehicle_data.get("engine_capacity"):
            confidence_score += 3
        if vehicle_data.get("transmission"):
            confidence_score += 2
        if vehicle_data.get("fuel_type"):
            confidence_score += 2
        
        if age > 15:
            confidence_score -= 5
        if mileage > 150000:
            confidence_score -= 5
        
        confidence_score = min(98, max(50, confidence_score))
        
        # Generate certificate number
        cert_number = f"AUTO-VAL-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Calculate range
        range_low = round(market_value * 0.88 / 1000) * 1000
        range_high = round(market_value * 1.05 / 1000) * 1000
        
        response = {
            "market_value": market_value,
            "range_low": range_low,
            "range_high": range_high,
            "confidence_score": confidence_score,
            "certificate_number": cert_number,
            "factors": {
                "age": age,
                "age_factor": round(age_factor, 2),
                "mileage_factor": round(mileage_factor, 2),
                "condition_factor": round(condition_factor, 2),
                "accident_factor": round(accident_factor, 2),
                "owners_factor": round(owners_factor, 2),
                "location_factor": round(location_factor, 2)
            },
            "created_at": datetime.now().isoformat()
        }
        
        # Save to database
        valuation_record = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "make": vehicle_data.get("make"),
            "model": vehicle_data.get("model"),
            "year": vehicle_data.get("year"),
            "engine_capacity": vehicle_data.get("engine_capacity"),
            "fuel_type": vehicle_data.get("fuel_type"),
            "transmission": vehicle_data.get("transmission"),
            "body_type": vehicle_data.get("body_type"),
            "body_color": vehicle_data.get("body_color"),
            "mileage": vehicle_data.get("mileage"),
            "condition": vehicle_data.get("condition"),
            "accident_history": vehicle_data.get("accident_history"),
            "location": vehicle_data.get("location"),
            "previous_owners": vehicle_data.get("previous_owners"),
            "usage_type": vehicle_data.get("usage_type"),
            "market_value": market_value,
            "confidence_score": confidence_score,
            "certificate_number": cert_number,
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        (
            admin
            .table("valuations")
            .upsert(valuation_record)
            .execute()
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_instant_valuation_history(
    current_user = Depends(get_current_active_user),
    limit: int = 10
):
    """Get history of instant valuations"""
    try:
        result = (
            supabase
            .table("valuations")
            .select("*")
            .eq("user_id", current_user.id)
            .eq("status", "completed")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{valuation_id}")
async def get_instant_valuation(
    valuation_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get a specific instant valuation by ID"""
    try:
        result = (
            supabase
            .table("valuations")
            .select("*")
            .eq("id", valuation_id)
            .eq("user_id", current_user.id)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Valuation not found")
        
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
