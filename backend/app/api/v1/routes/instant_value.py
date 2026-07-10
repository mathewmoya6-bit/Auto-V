# app/api/v1/routes/instant_value.py
# =============================================================================
# AUTO-V API - Instant Value Routes
# =============================================================================
"""
Instant Vehicle Valuation Endpoints

These endpoints provide quick, real-time vehicle valuations without requiring
a full assessment. The valuation is calculated based on vehicle details
including make, model, year, mileage, condition, and location.

No service fee is charged here - payment is handled separately by the
payments module. This is a pure calculation endpoint.
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
import random
import uuid

from fastapi import APIRouter, Depends, status, HTTPException, Query

from app.core.security import get_current_user, get_current_admin_user
from app.core.database import supabase, admin
from app.schemas.user import UserProfile
from app.schemas.instant_value import (
    InstantValueRequest,
    InstantValueResponse,
    InstantValueHistoryResponse,
    InstantValueStats,
    BulkInstantValueRequest,
    BulkInstantValueResponse
)
from app.services.instant_value_service import InstantValueService

router = APIRouter(tags=["Instant Value"])


def get_instant_value_service() -> InstantValueService:
    return InstantValueService()


# ─── Vehicle Reference Data ──────────────────────────────────────────

# Base values by vehicle type (in KES)
BASE_VALUES = {
    "Car": 2000000,
    "Bike": 300000,
    "Tricycle": 200000
}

# Condition factors
CONDITION_FACTORS = {
    "Excellent": 1.2,
    "Good": 1.0,
    "Fair": 0.8,
    "Poor": 0.6
}

# Accident history factors
ACCIDENT_FACTORS = {
    "None": 1.0,
    "Minor": 0.85,
    "Major": 0.6,
    "WriteOff": 0.3
}

# Location factors (county-based demand)
LOCATION_FACTORS = {
    "Nairobi": 1.1,
    "Mombasa": 1.05,
    "Kisumu": 0.95,
    "Nakuru": 0.98,
    "Eldoret": 0.95,
    "Kiambu": 1.08,
    "Kajiado": 1.05,
    "Machakos": 1.02,
    "Meru": 0.95,
    "Nyeri": 0.93,
    "Embu": 0.90,
    "Bungoma": 0.88,
    "Kakamega": 0.87,
    "Kitale": 0.85,
    "Garissa": 0.80,
    "Other": 0.9
}

# Fuel type factors
FUEL_FACTORS = {
    "Petrol": 1.0,
    "Diesel": 1.05,
    "Hybrid": 1.1,
    "Electric": 1.15
}

# Transmission factors
TRANSMISSION_FACTORS = {
    "Automatic": 1.05,
    "Manual": 1.0,
    "CVT": 1.02
}


# ─── Core Calculation ────────────────────────────────────────────────

def calculate_instant_value(vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core calculation engine for instant vehicle valuation.
    Returns market value, range, confidence score, and factors.
    """
    current_year = datetime.now().year
    
    # Extract vehicle data with defaults
    vehicle_type = vehicle_data.get("type", "Car")
    year = vehicle_data.get("year", current_year)
    mileage = vehicle_data.get("mileage", 0)
    condition = vehicle_data.get("condition", "Good")
    accident_history = vehicle_data.get("accident_history", "None")
    previous_owners = vehicle_data.get("previous_owners", 1)
    location = vehicle_data.get("location", "Other")
    fuel_type = vehicle_data.get("fuel_type", "Petrol")
    transmission = vehicle_data.get("transmission", "Manual")
    body_type = vehicle_data.get("body_type", "Sedan")
    engine_capacity = vehicle_data.get("engine_capacity", 1500)
    has_service_history = vehicle_data.get("service_history", False)
    
    # Calculate age
    age = current_year - year
    age = max(0, age)
    
    # Base value by type
    base_value = BASE_VALUES.get(vehicle_type, 1000000)
    
    # Adjust base value for body type
    body_type_multipliers = {
        "SUV": 1.2,
        "Pickup": 1.15,
        "Van": 1.1,
        "Sedan": 1.0,
        "Hatchback": 0.95,
        "Coupe": 1.05,
        "Convertible": 1.08,
        "Wagon": 0.98,
        "Other": 1.0
    }
    body_multiplier = body_type_multipliers.get(body_type, 1.0)
    base_value = base_value * body_multiplier
    
    # Adjust for engine capacity
    if engine_capacity > 3000:
        engine_multiplier = 1.2
    elif engine_capacity > 2000:
        engine_multiplier = 1.1
    elif engine_capacity > 1500:
        engine_multiplier = 1.05
    else:
        engine_multiplier = 1.0
    base_value = base_value * engine_multiplier
    
    # Depreciation: 10-15% per year
    depreciation_rate = 0.12
    age_factor = max(0.15, 1 - (depreciation_rate * age))
    
    # Mileage factor: reduce value based on mileage
    mileage_factor = max(0.25, 1 - (mileage / 200000))
    
    # Condition factor
    condition_factor = CONDITION_FACTORS.get(condition, 1.0)
    
    # Accident history factor
    accident_factor = ACCIDENT_FACTORS.get(accident_history, 1.0)
    
    # Previous owners factor
    owners_factor = max(0.6, 1 - (previous_owners * 0.025))
    
    # Location factor
    location_factor = LOCATION_FACTORS.get(location, 0.9)
    
    # Fuel type factor
    fuel_factor = FUEL_FACTORS.get(fuel_type, 1.0)
    
    # Transmission factor
    transmission_factor = TRANSMISSION_FACTORS.get(transmission, 1.0)
    
    # Service history bonus
    service_bonus = 1.05 if has_service_history else 1.0
    
    # Calculate final market value
    market_value = (
        base_value *
        age_factor *
        mileage_factor *
        condition_factor *
        accident_factor *
        owners_factor *
        location_factor *
        fuel_factor *
        transmission_factor *
        service_bonus
    )
    
    # Add some randomness for realism (±5%)
    random_factor = 1 + (random.random() - 0.5) * 0.1
    market_value = market_value * random_factor
    
    # Round to nearest 1000
    market_value = round(market_value / 1000) * 1000
    
    # Calculate confidence score
    confidence_score = 60  # Base confidence
    
    # Increase confidence with complete data
    if vehicle_data.get("make") and vehicle_data.get("model"):
        confidence_score += 5
    if body_type and body_type != "Other":
        confidence_score += 3
    if engine_capacity and engine_capacity > 0:
        confidence_score += 3
    if transmission:
        confidence_score += 2
    if fuel_type:
        confidence_score += 2
    if has_service_history:
        confidence_score += 5
    
    # Decrease confidence with age and mileage
    if age > 15:
        confidence_score -= 5
    if mileage > 150000:
        confidence_score -= 5
    if previous_owners > 3:
        confidence_score -= 3
    
    confidence_score = min(98, max(45, confidence_score))
    
    # Generate certificate number
    cert_number = f"AUTO-VAL-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    
    # Calculate range (±10-15%)
    range_low = round(market_value * 0.88 / 1000) * 1000
    range_high = round(market_value * 1.08 / 1000) * 1000
    
    return {
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
            "location_factor": round(location_factor, 2),
            "fuel_factor": round(fuel_factor, 2),
            "transmission_factor": round(transmission_factor, 2),
            "service_bonus": round(service_bonus, 2),
            "base_value": base_value,
            "body_type": body_type,
            "engine_capacity": engine_capacity
        },
        "vehicle_details": {
            "type": vehicle_type,
            "year": year,
            "mileage": mileage,
            "condition": condition,
            "location": location
        }
    }


# ─── Endpoints ──────────────────────────────────────────────────────

@router.post("/calculate", response_model=InstantValueResponse, status_code=status.HTTP_200_OK)
async def calculate_instant_value(
    request: InstantValueRequest,
    current_user: UserProfile = Depends(get_current_user),
    service: InstantValueService = Depends(get_instant_value_service),
):
    """
    Calculate instant vehicle valuation.
    
    This endpoint provides a quick, real-time vehicle valuation based on
    the provided vehicle details. The valuation is calculated using
    multiple factors including:
    - Vehicle type and body style
    - Age and depreciation
    - Mileage
    - Condition
    - Accident history
    - Previous owners
    - Location (county)
    - Fuel type
    - Transmission
    - Service history
    
    No payment is required for this calculation. The result includes
    market value, price range, confidence score, and a certificate number.
    """
    try:
        # Convert request to dict
        vehicle_data = request.model_dump()
        
        # Calculate valuation
        result = calculate_instant_value(vehicle_data)
        
        # Save to history (if user is authenticated)
        if current_user:
            history_record = {
                "user_id": str(current_user.id),
                "make": request.make,
                "model": request.model,
                "year": request.year,
                "mileage": request.mileage,
                "condition": request.condition,
                "location": request.location,
                "market_value": result["market_value"],
                "confidence_score": result["confidence_score"],
                "certificate_number": result["certificate_number"],
                "factors": result["factors"],
                "vehicle_details": result["vehicle_details"],
                "created_at": datetime.now().isoformat()
            }
            
            (
                admin
                .table("instant_valuations")
                .insert(history_record)
                .execute()
            )
        
        return {
            **result,
            "user_id": str(current_user.id) if current_user else None,
            "request_id": str(uuid.uuid4()),
            "calculated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=BulkInstantValueResponse)
async def bulk_instant_value(
    request: BulkInstantValueRequest,
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Calculate instant valuations for multiple vehicles at once.
    Useful for fleet valuation or comparison shopping.
    """
    try:
        results = []
        total_value = 0
        average_value = 0
        highest_value = 0
        lowest_value = float('inf')
        
        for vehicle_data in request.vehicles:
            result = calculate_instant_value(vehicle_data)
            
            market_value = result["market_value"]
            total_value += market_value
            highest_value = max(highest_value, market_value)
            lowest_value = min(lowest_value, market_value)
            
            # Save each to history
            if current_user:
                history_record = {
                    "user_id": str(current_user.id),
                    "make": vehicle_data.get("make"),
                    "model": vehicle_data.get("model"),
                    "year": vehicle_data.get("year"),
                    "mileage": vehicle_data.get("mileage", 0),
                    "condition": vehicle_data.get("condition", "Good"),
                    "location": vehicle_data.get("location", "Other"),
                    "market_value": market_value,
                    "confidence_score": result["confidence_score"],
                    "certificate_number": result["certificate_number"],
                    "factors": result["factors"],
                    "vehicle_details": result["vehicle_details"],
                    "created_at": datetime.now().isoformat()
                }
                
                (
                    admin
                    .table("instant_valuations")
                    .insert(history_record)
                    .execute()
                )
            
            results.append({
                "vehicle": vehicle_data,
                "valuation": result
            })
        
        count = len(results)
        average_value = total_value / count if count > 0 else 0
        
        return {
            "results": results,
            "summary": {
                "total_vehicles": count,
                "total_value": round(total_value, 2),
                "average_value": round(average_value, 2),
                "highest_value": round(highest_value, 2) if count > 0 else 0,
                "lowest_value": round(lowest_value, 2) if count > 0 else 0
            },
            "user_id": str(current_user.id) if current_user else None,
            "calculated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[InstantValueHistoryResponse])
async def get_instant_value_history(
    current_user: UserProfile = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: InstantValueService = Depends(get_instant_value_service),
):
    """
    Get history of instant valuations for the current user.
    """
    try:
        result = (
            supabase
            .table("instant_valuations")
            .select("*")
            .eq("user_id", str(current_user.id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{valuation_id}", response_model=InstantValueHistoryResponse)
async def get_instant_valuation_by_id(
    valuation_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: InstantValueService = Depends(get_instant_value_service),
):
    """
    Get a specific instant valuation by ID.
    """
    try:
        result = (
            supabase
            .table("instant_valuations")
            .select("*")
            .eq("id", str(valuation_id))
            .eq("user_id", str(current_user.id))
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Valuation not found")
        
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=InstantValueStats)
async def get_instant_value_stats(
    current_user: UserProfile = Depends(get_current_user),
    service: InstantValueService = Depends(get_instant_value_service),
):
    """
    Get statistics about user's instant valuations.
    """
    try:
        result = (
            supabase
            .table("instant_valuations")
            .select("market_value, confidence_score, created_at")
            .eq("user_id", str(current_user.id))
            .execute()
        )
        
        data = result.data
        
        if not data:
            return {
                "total_valuations": 0,
                "average_value": 0,
                "average_confidence": 0,
                "highest_value": 0,
                "lowest_value": 0,
                "last_30_days": 0,
                "most_common_make": None,
                "most_common_model": None
            }
        
        total = len(data)
        values = [v.get("market_value", 0) for v in data if v.get("market_value")]
        confidences = [v.get("confidence_score", 0) for v in data if v.get("confidence_score")]
        
        # Count last 30 days
        thirty_days_ago = datetime.now().timestamp() - (30 * 24 * 60 * 60)
        last_30_days = sum(1 for v in data if v.get("created_at") and 
                          datetime.fromisoformat(v["created_at"]).timestamp() > thirty_days_ago)
        
        return {
            "total_valuations": total,
            "average_value": round(sum(values) / len(values), 2) if values else 0,
            "average_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0,
            "highest_value": max(values) if values else 0,
            "lowest_value": min(values) if values else 0,
            "last_30_days": last_30_days,
            "most_common_make": None,  # Would need additional query
            "most_common_model": None   # Would need additional query
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{valuation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instant_valuation(
    valuation_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: InstantValueService = Depends(get_instant_value_service),
):
    """
    Delete an instant valuation from history.
    """
    try:
        # Check ownership
        check = (
            supabase
            .table("instant_valuations")
            .select("user_id")
            .eq("id", str(valuation_id))
            .execute()
        )
        
        if not check.data:
            raise HTTPException(status_code=404, detail="Valuation not found")
        
        if check.data[0]["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to delete this valuation")
        
        (
            admin
            .table("instant_valuations")
            .delete()
            .eq("id", str(valuation_id))
            .execute()
        )
        
        return None
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/all", status_code=status.HTTP_204_NO_CONTENT)
async def clear_instant_valuation_history(
    current_user: UserProfile = Depends(get_current_user),
    service: InstantValueService = Depends(get_instant_value_service),
):
    """
    Clear all instant valuation history for the current user.
    """
    try:
        (
            admin
            .table("instant_valuations")
            .delete()
            .eq("user_id", str(current_user.id))
            .execute()
        )
        return None
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Admin Endpoints ──────────────────────────────────────────────────

@router.get("/admin/all", response_model=List[InstantValueHistoryResponse])
async def admin_list_all_instant_valuations(
    current_admin: UserProfile = Depends(get_current_admin_user),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: InstantValueService = Depends(get_instant_value_service),
):
    """
    List all instant valuations across all users (Admin only).
    """
    try:
        result = (
            supabase
            .table("instant_valuations")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/stats", response_model=dict)
async def admin_get_instant_value_stats(
    current_admin: UserProfile = Depends(get_current_admin_user),
    service: InstantValueService = Depends(get_instant_value_service),
):
    """
    Get global instant valuation statistics (Admin only).
    """
    try:
        result = (
            supabase
            .table("instant_valuations")
            .select("market_value, confidence_score, created_at")
            .execute()
        )
        
        data = result.data
        
        if not data:
            return {
                "total_valuations": 0,
                "average_value": 0,
                "average_confidence": 0,
                "total_users": 0
            }
        
        total = len(data)
        values = [v.get("market_value", 0) for v in data if v.get("market_value")]
        confidences = [v.get("confidence_score", 0) for v in data if v.get("confidence_score")]
        
        # Get unique users
        users = set(v.get("user_id") for v in data if v.get("user_id"))
        
        return {
            "total_valuations": total,
            "average_value": round(sum(values) / len(values), 2) if values else 0,
            "average_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0,
            "total_users": len(users)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
