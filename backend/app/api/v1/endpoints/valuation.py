from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import uuid
import random
from app.core.database import supabase, admin
from app.schemas.valuations import (
    ValuationCreate,
    ValuationUpdate,
    ValuationResponse,
    InstantValuationRequest,
    InstantValuationResponse,
    VehicleAssessmentRequest,
    VehicleAssessmentResponse,
    AssessmentFactor
)
from app.core.security import get_current_active_user

router = APIRouter(tags=["Valuations"])


@router.post("/", response_model=ValuationResponse)
async def create_valuation(
    valuation: ValuationCreate,
    current_user = Depends(get_current_active_user)
):
    """Create a new valuation record"""
    try:
        valuation_data = valuation.model_dump()
        valuation_data["user_id"] = current_user.id
        valuation_data["status"] = "pending"
        valuation_data["created_at"] = datetime.now().isoformat()
        
        result = (
            admin
            .table("valuations")
            .insert(valuation_data)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create valuation")
        
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ValuationResponse])
async def get_user_valuations(
    current_user = Depends(get_current_active_user),
    limit: int = 50,
    offset: int = 0
):
    """Get all valuations for the current user"""
    try:
        result = (
            supabase
            .table("valuations")
            .select("*")
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[ValuationResponse])
async def get_valuation_history(
    current_user = Depends(get_current_active_user),
    limit: int = 10
):
    """Get valuation history for the current user"""
    try:
        result = (
            supabase
            .table("valuations")
            .select("*")
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{valuation_id}", response_model=ValuationResponse)
async def get_valuation(
    valuation_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get a specific valuation by ID"""
    try:
        result = (
            supabase
            .table("valuations")
            .select("*")
            .eq("id", valuation_id)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Valuation not found")
        
        valuation = result.data[0]
        
        # Check if user owns this valuation
        if valuation["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this valuation")
        
        return valuation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{valuation_id}", response_model=ValuationResponse)
async def update_valuation(
    valuation_id: str,
    valuation_update: ValuationUpdate,
    current_user = Depends(get_current_active_user)
):
    """Update a valuation record"""
    try:
        # Check ownership
        check = (
            supabase
            .table("valuations")
            .select("user_id")
            .eq("id", valuation_id)
            .execute()
        )
        
        if not check.data:
            raise HTTPException(status_code=404, detail="Valuation not found")
        
        if check.data[0]["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this valuation")
        
        update_data = valuation_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now().isoformat()
        
        result = (
            admin
            .table("valuations")
            .update(update_data)
            .eq("id", valuation_id)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Valuation not found")
        
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instant", response_model=InstantValuationResponse)
async def instant_valuation(
    request: InstantValuationRequest,
    current_user = Depends(get_current_active_user)
):
    """
    Get instant AI-powered vehicle valuation
    This calculates market value based on vehicle details
    No service fee is charged here - payment is handled separately
    """
    try:
        vehicle = request.vehicle
        
        # Calculate base value based on vehicle type and year
        current_year = datetime.now().year
        age = current_year - vehicle.get("year", current_year)
        
        # Base values by vehicle type (in KES)
        base_values = {
            "Car": 2000000,
            "Bike": 300000,
            "Tricycle": 200000
        }
        
        base_value = base_values.get(vehicle.get("type", "Car"), 1000000)
        
        # Depreciation: 10-15% per year
        depreciation_rate = 0.12  # 12% per year
        age_factor = max(0.2, 1 - (depreciation_rate * age))
        
        # Mileage factor: reduce value based on mileage
        mileage = vehicle.get("mileage", 0)
        mileage_factor = max(0.3, 1 - (mileage / 200000))  # Max 70% reduction
        
        # Condition factor
        condition_factors = {
            "Excellent": 1.2,
            "Good": 1.0,
            "Fair": 0.8,
            "Poor": 0.6
        }
        condition = vehicle.get("condition", "Good")
        condition_factor = condition_factors.get(condition, 1.0)
        
        # Accident history factor
        accident_factors = {
            "None": 1.0,
            "Minor": 0.85,
            "Major": 0.6,
            "WriteOff": 0.3
        }
        accident = vehicle.get("accident_history", "None")
        accident_factor = accident_factors.get(accident, 1.0)
        
        # Previous owners factor
        owners = vehicle.get("previous_owners", 1)
        owners_factor = max(0.7, 1 - (owners * 0.03))
        
        # Location factor (different counties have different demand)
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
        location = vehicle.get("location", "Other")
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
        
        # Add some randomness for realism (±5%)
        random_factor = 1 + (random.random() - 0.5) * 0.1
        market_value = market_value * random_factor
        
        # Round to nearest 1000
        market_value = round(market_value / 1000) * 1000
        
        # Calculate confidence score based on data completeness
        confidence_score = 70  # Base confidence
        
        # Increase confidence with more complete data
        if vehicle.get("make") and vehicle.get("model"):
            confidence_score += 5
        if vehicle.get("body_type"):
            confidence_score += 3
        if vehicle.get("engine_capacity"):
            confidence_score += 3
        if vehicle.get("transmission"):
            confidence_score += 2
        if vehicle.get("fuel_type"):
            confidence_score += 2
        
        # Decrease confidence with age
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
            "valuation_id": request.valuation_id,
            "created_at": datetime.now().isoformat()
        }
        
        # Save the instant valuation to database
        valuation_record = {
            "id": request.valuation_id or str(uuid.uuid4()),
            "user_id": current_user.id,
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "year": vehicle.get("year"),
            "engine_capacity": vehicle.get("engine_capacity"),
            "fuel_type": vehicle.get("fuel_type"),
            "transmission": vehicle.get("transmission"),
            "body_type": vehicle.get("body_type"),
            "body_color": vehicle.get("body_color"),
            "mileage": vehicle.get("mileage"),
            "condition": vehicle.get("condition"),
            "accident_history": vehicle.get("accident_history"),
            "location": vehicle.get("location"),
            "previous_owners": vehicle.get("previous_owners"),
            "usage_type": vehicle.get("usage_type"),
            "market_value": market_value,
            "confidence_score": confidence_score,
            "certificate_number": cert_number,
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Save to database
        (
            admin
            .table("valuations")
            .upsert(valuation_record)
            .execute()
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assess", response_model=VehicleAssessmentResponse)
async def assess_vehicle(
    request: VehicleAssessmentRequest,
    current_user = Depends(get_current_active_user)
):
    """
    Comprehensive vehicle assessment including:
    - Market value
    - Condition rating
    - Maintenance cost estimate
    - Depreciation forecast
    - Investment recommendation
    """
    try:
        vehicle = request.vehicle
        
        # ─── Market Value Calculation ──────────────────────────────
        current_year = datetime.now().year
        age = current_year - vehicle.get("year", current_year)
        
        base_values = {
            "Car": 2000000,
            "Bike": 300000,
            "Tricycle": 200000
        }
        base_value = base_values.get(vehicle.get("type", "Car"), 1000000)
        
        # Factors
        depreciation_rate = 0.12
        age_factor = max(0.2, 1 - (depreciation_rate * age))
        
        mileage = vehicle.get("mileage", 0)
        mileage_factor = max(0.3, 1 - (mileage / 200000))
        
        condition_factors = {
            "Excellent": 1.2,
            "Good": 1.0,
            "Fair": 0.8,
            "Poor": 0.6
        }
        condition = vehicle.get("condition", "Good")
        condition_factor = condition_factors.get(condition, 1.0)
        
        accident_factors = {
            "None": 1.0,
            "Minor": 0.85,
            "Major": 0.6,
            "WriteOff": 0.3
        }
        accident = vehicle.get("accident_history", "None")
        accident_factor = accident_factors.get(accident, 1.0)
        
        owners = vehicle.get("previous_owners", 1)
        owners_factor = max(0.7, 1 - (owners * 0.03))
        
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
        location = vehicle.get("location", "Other")
        location_factor = location_factors.get(location, 0.9)
        
        market_value = (
            base_value * age_factor * mileage_factor * 
            condition_factor * accident_factor * owners_factor * location_factor
        )
        market_value = round(market_value / 1000) * 1000
        
        # ─── Condition Assessment ──────────────────────────────────
        condition_score = 0
        condition_details = []
        
        # Check exterior condition
        if vehicle.get("body_condition", "Good") == "Excellent":
            condition_score += 25
            condition_details.append({"category": "Exterior", "score": 25, "status": "Excellent"})
        elif vehicle.get("body_condition", "Good") == "Good":
            condition_score += 18
            condition_details.append({"category": "Exterior", "score": 18, "status": "Good"})
        else:
            condition_score += 10
            condition_details.append({"category": "Exterior", "score": 10, "status": "Fair"})
        
        # Check interior condition
        if vehicle.get("interior_condition", "Good") == "Excellent":
            condition_score += 20
            condition_details.append({"category": "Interior", "score": 20, "status": "Excellent"})
        elif vehicle.get("interior_condition", "Good") == "Good":
            condition_score += 15
            condition_details.append({"category": "Interior", "score": 15, "status": "Good"})
        else:
            condition_score += 8
            condition_details.append({"category": "Interior", "score": 8, "status": "Fair"})
        
        # Check mechanical condition
        if vehicle.get("mechanical_condition", "Good") == "Excellent":
            condition_score += 30
            condition_details.append({"category": "Mechanical", "score": 30, "status": "Excellent"})
        elif vehicle.get("mechanical_condition", "Good") == "Good":
            condition_score += 22
            condition_details.append({"category": "Mechanical", "score": 22, "status": "Good"})
        else:
            condition_score += 12
            condition_details.append({"category": "Mechanical", "score": 12, "status": "Fair"})
        
        # Check tire condition
        if vehicle.get("tire_condition", "Good") == "Excellent":
            condition_score += 15
            condition_details.append({"category": "Tires", "score": 15, "status": "Excellent"})
        elif vehicle.get("tire_condition", "Good") == "Good":
            condition_score += 10
            condition_details.append({"category": "Tires", "score": 10, "status": "Good"})
        else:
            condition_score += 5
            condition_details.append({"category": "Tires", "score": 5, "status": "Fair"})
        
        # Check service history
        if vehicle.get("service_history", False):
            condition_score += 10
            condition_details.append({"category": "Service History", "score": 10, "status": "Verified"})
        else:
            condition_details.append({"category": "Service History", "score": 0, "status": "Unverified"})
        
        # Determine overall condition rating
        if condition_score >= 85:
            overall_condition = "Excellent"
            condition_color = "#22c55e"
        elif condition_score >= 70:
            overall_condition = "Good"
            condition_color = "#eab308"
        elif condition_score >= 50:
            overall_condition = "Fair"
            condition_color = "#f59e0b"
        else:
            overall_condition = "Poor"
            condition_color = "#ef4444"
        
        # ─── Maintenance Cost Estimate ─────────────────────────────
        maintenance_cost = 0
        
        # Base maintenance by vehicle type
        maintenance_base = {
            "Car": 50000,
            "Bike": 15000,
            "Tricycle": 20000
        }
        maintenance_cost += maintenance_base.get(vehicle.get("type", "Car"), 30000)
        
        # Age factor for maintenance
        if age < 3:
            maintenance_cost *= 0.5
        elif age < 7:
            maintenance_cost *= 0.8
        elif age < 12:
            maintenance_cost *= 1.2
        else:
            maintenance_cost *= 1.5
        
        # Mileage factor
        if mileage > 100000:
            maintenance_cost *= 1.3
        elif mileage > 50000:
            maintenance_cost *= 1.1
        
        # Condition factor
        if condition == "Excellent":
            maintenance_cost *= 0.7
        elif condition == "Good":
            maintenance_cost *= 0.9
        elif condition == "Fair":
            maintenance_cost *= 1.2
        else:
            maintenance_cost *= 1.5
        
        maintenance_cost = round(maintenance_cost / 1000) * 1000
        
        # ─── Depreciation Forecast ──────────────────────────────────
        depreciation_forecast = []
        for year in range(1, 6):
            future_value = market_value * (1 - depreciation_rate * year)
            depreciation_forecast.append({
                "year": f"Year {year}",
                "projected_value": round(future_value / 1000) * 1000,
                "depreciation": round((market_value - future_value) / 1000) * 1000,
                "percentage": round((1 - (future_value / market_value)) * 100, 1)
            })
        
        # ─── Investment Recommendation ─────────────────────────────
        recommendations = []
        recommendation_score = 0
        
        # Price to value ratio
        if request.price and request.price > 0:
            price_to_value = request.price / market_value
            if price_to_value < 0.8:
                recommendations.append("Excellent value - price is below market value")
                recommendation_score += 20
            elif price_to_value < 0.95:
                recommendations.append("Good value - price is slightly below market value")
                recommendation_score += 15
            elif price_to_value < 1.05:
                recommendations.append("Fair value - price is close to market value")
                recommendation_score += 10
            else:
                recommendations.append("Overpriced - price is above market value")
                recommendation_score -= 10
        
        # Condition recommendation
        if overall_condition == "Excellent":
            recommendations.append("Excellent condition - minimal maintenance expected")
            recommendation_score += 15
        elif overall_condition == "Good":
            recommendations.append("Good condition - regular maintenance recommended")
            recommendation_score += 10
        elif overall_condition == "Fair":
            recommendations.append("Fair condition - budget for repairs")
            recommendation_score += 5
        else:
            recommendations.append("Poor condition - significant repairs needed")
            recommendation_score -= 5
        
        # Age recommendation
        if age < 3:
            recommendations.append("Recent model - good long-term investment")
            recommendation_score += 10
        elif age < 7:
            recommendations.append("Mid-age vehicle - good value for money")
            recommendation_score += 5
        elif age < 12:
            recommendations.append("Older vehicle - depreciation will slow")
        else:
            recommendations.append("Vintage vehicle - collector potential")
        
        # Mileage recommendation
        if mileage < 30000:
            recommendations.append("Low mileage - excellent find")
            recommendation_score += 10
        elif mileage < 60000:
            recommendations.append("Average mileage - reasonable wear")
            recommendation_score += 5
        elif mileage < 100000:
            recommendations.append("Above average mileage - check service history")
        else:
            recommendations.append("High mileage - significant wear expected")
            recommendation_score -= 5
        
        # Determine overall recommendation
        if recommendation_score >= 40:
            investment_rating = "Strong Buy"
            investment_color = "#22c55e"
        elif recommendation_score >= 25:
            investment_rating = "Buy"
            investment_color = "#3b82f6"
        elif recommendation_score >= 10:
            investment_rating = "Hold"
            investment_color = "#eab308"
        elif recommendation_score >= 0:
            investment_rating = "Caution"
            investment_color = "#f59e0b"
        else:
            investment_rating = "Avoid"
            investment_color = "#ef4444"
        
        # ─── Response ──────────────────────────────────────────────
        response = {
            "market_value": market_value,
            "condition_assessment": {
                "overall_rating": overall_condition,
                "score": condition_score,
                "color": condition_color,
                "details": condition_details
            },
            "maintenance_cost": maintenance_cost,
            "depreciation_forecast": depreciation_forecast,
            "investment_recommendation": {
                "rating": investment_rating,
                "color": investment_color,
                "score": recommendation_score,
                "recommendations": recommendations[:5]  # Top 5 recommendations
            },
            "valuation_id": request.valuation_id,
            "generated_at": datetime.now().isoformat()
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
