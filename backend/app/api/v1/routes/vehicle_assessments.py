# app/api/v1/routes/vehicle_assessments.py
# =============================================================================
# AUTO-V API - Vehicle Assessment Routes
# =============================================================================
"""
Comprehensive Vehicle Assessment Endpoints

These endpoints provide detailed vehicle assessments including:
- Market value calculation
- Condition rating with detailed breakdown (exterior, interior, mechanical, tires, service history)
- Maintenance cost estimation
- 5-year depreciation forecast
- Investment recommendation (Strong Buy, Buy, Hold, Caution, Avoid)
- Comprehensive scoring system

Unlike the instant value endpoint which provides a quick estimate,
this assessment provides a detailed, multi-faceted evaluation suitable
for purchase decisions, insurance, or financing.
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, status, HTTPException, Query

from app.core.security import get_current_user, get_current_admin_user
from app.core.database import supabase, admin
from app.schemas.user import UserProfile
from app.schemas.vehicle_assessment import (
    VehicleAssessmentRequest,
    VehicleAssessmentResponse,
    ConditionAssessment,
    AssessmentFactor,
    DepreciationForecastItem,
    InvestmentRecommendation,
    AssessmentHistoryResponse,
    AssessmentStats,
    BulkAssessmentRequest,
    BulkAssessmentResponse,
    AssessmentComparisonRequest,
    AssessmentComparisonResponse
)
from app.services.vehicle_assessment_service import VehicleAssessmentService

router = APIRouter(tags=["Vehicle Assessments"])


def get_assessment_service() -> VehicleAssessmentService:
    return VehicleAssessmentService()


# ─── Constants ──────────────────────────────────────────────────────

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

# Location factors
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


# ─── Core Assessment Engine ─────────────────────────────────────────

def perform_vehicle_assessment(vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core assessment engine that evaluates all aspects of a vehicle.
    Returns comprehensive assessment with condition, market value,
    maintenance costs, depreciation forecast, and investment recommendation.
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
    
    # Individual condition ratings (for detailed breakdown)
    exterior_condition = vehicle_data.get("body_condition", condition)
    interior_condition = vehicle_data.get("interior_condition", condition)
    mechanical_condition = vehicle_data.get("mechanical_condition", condition)
    tire_condition = vehicle_data.get("tire_condition", "Good")
    
    # Calculate age
    age = current_year - year
    age = max(0, age)
    
    # ─── Market Value Calculation ──────────────────────────────────
    
    # Base value by type
    base_value = BASE_VALUES.get(vehicle_type, 1000000)
    
    # Adjust for body type
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
    
    # Apply factors
    depreciation_rate = 0.12
    age_factor = max(0.15, 1 - (depreciation_rate * age))
    mileage_factor = max(0.25, 1 - (mileage / 200000))
    condition_factor = CONDITION_FACTORS.get(condition, 1.0)
    accident_factor = ACCIDENT_FACTORS.get(accident_history, 1.0)
    owners_factor = max(0.6, 1 - (previous_owners * 0.025))
    location_factor = LOCATION_FACTORS.get(location, 0.9)
    fuel_factor = FUEL_FACTORS.get(fuel_type, 1.0)
    transmission_factor = TRANSMISSION_FACTORS.get(transmission, 1.0)
    service_bonus = 1.05 if has_service_history else 1.0
    
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
    market_value = round(market_value / 1000) * 1000
    
    # ─── Condition Assessment ──────────────────────────────────────
    
    condition_score = 0
    condition_details = []
    max_score = 100
    
    # Exterior (25 points)
    exterior_scores = {"Excellent": 25, "Good": 18, "Fair": 10, "Poor": 5}
    exterior_score = exterior_scores.get(exterior_condition, 10)
    condition_score += exterior_score
    condition_details.append({
        "category": "Exterior",
        "score": exterior_score,
        "max_score": 25,
        "status": exterior_condition,
        "icon": "🚗",
        "description": f"Exterior condition is {exterior_condition.lower()}"
    })
    
    # Interior (20 points)
    interior_scores = {"Excellent": 20, "Good": 15, "Fair": 8, "Poor": 4}
    interior_score = interior_scores.get(interior_condition, 8)
    condition_score += interior_score
    condition_details.append({
        "category": "Interior",
        "score": interior_score,
        "max_score": 20,
        "status": interior_condition,
        "icon": "🪑",
        "description": f"Interior condition is {interior_condition.lower()}"
    })
    
    # Mechanical (30 points)
    mechanical_scores = {"Excellent": 30, "Good": 22, "Fair": 12, "Poor": 6}
    mechanical_score = mechanical_scores.get(mechanical_condition, 12)
    condition_score += mechanical_score
    condition_details.append({
        "category": "Mechanical",
        "score": mechanical_score,
        "max_score": 30,
        "status": mechanical_condition,
        "icon": "🔧",
        "description": f"Mechanical condition is {mechanical_condition.lower()}"
    })
    
    # Tires (15 points)
    tire_scores = {"Excellent": 15, "Good": 10, "Fair": 5, "Poor": 2}
    tire_score = tire_scores.get(tire_condition, 5)
    condition_score += tire_score
    condition_details.append({
        "category": "Tires",
        "score": tire_score,
        "max_score": 15,
        "status": tire_condition,
        "icon": "🛞",
        "description": f"Tire condition is {tire_condition.lower()}"
    })
    
    # Service History (10 points)
    if has_service_history:
        condition_score += 10
        condition_details.append({
            "category": "Service History",
            "score": 10,
            "max_score": 10,
            "status": "Verified",
            "icon": "📋",
            "description": "Service history is verified and complete"
        })
    else:
        condition_details.append({
            "category": "Service History",
            "score": 0,
            "max_score": 10,
            "status": "Unverified",
            "icon": "📋",
            "description": "Service history is not available"
        })
    
    # Determine overall condition rating
    if condition_score >= 85:
        overall_condition = "Excellent"
        condition_color = "#22c55e"
        condition_emoji = "🌟"
    elif condition_score >= 70:
        overall_condition = "Good"
        condition_color = "#eab308"
        condition_emoji = "👍"
    elif condition_score >= 50:
        overall_condition = "Fair"
        condition_color = "#f59e0b"
        condition_emoji = "👌"
    else:
        overall_condition = "Poor"
        condition_color = "#ef4444"
        condition_emoji = "⚠️"
    
    condition_percentage = round((condition_score / max_score) * 100)
    
    # ─── Maintenance Cost Estimate ─────────────────────────────────
    
    maintenance_base = {"Car": 50000, "Bike": 15000, "Tricycle": 20000}
    maintenance_cost = maintenance_base.get(vehicle_type, 30000)
    
    # Age factor
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
    
    # ─── Depreciation Forecast ─────────────────────────────────────
    
    depreciation_forecast = []
    for year_offset in range(1, 6):
        future_value = market_value * (1 - depreciation_rate * year_offset)
        projected_value = round(future_value / 1000) * 1000
        depreciation_amount = market_value - projected_value
        
        depreciation_forecast.append({
            "year": f"Year {year_offset}",
            "year_number": year_offset,
            "projected_value": projected_value,
            "depreciation": round(depreciation_amount / 1000) * 1000,
            "percentage": round((1 - (future_value / market_value)) * 100, 1),
            "status": "Good" if projected_value > market_value * 0.5 else "Fair"
        })
    
    # ─── Investment Recommendation ─────────────────────────────────
    
    recommendations = []
    recommendation_score = 0
    
    # Price to value ratio (if price provided)
    provided_price = vehicle_data.get("price", 0)
    if provided_price > 0:
        price_to_value = provided_price / market_value
        if price_to_value < 0.8:
            recommendations.append({
                "type": "price",
                "title": "Excellent Value",
                "description": "Price is below market value - great deal",
                "severity": "positive",
                "score": 20
            })
            recommendation_score += 20
        elif price_to_value < 0.95:
            recommendations.append({
                "type": "price",
                "title": "Good Value",
                "description": "Price is slightly below market value",
                "severity": "positive",
                "score": 15
            })
            recommendation_score += 15
        elif price_to_value < 1.05:
            recommendations.append({
                "type": "price",
                "title": "Fair Value",
                "description": "Price is close to market value",
                "severity": "neutral",
                "score": 10
            })
            recommendation_score += 10
        else:
            recommendations.append({
                "type": "price",
                "title": "Overpriced",
                "description": "Price is above market value - negotiate",
                "severity": "negative",
                "score": -10
            })
            recommendation_score -= 10
    
    # Condition recommendation
    if overall_condition == "Excellent":
        recommendations.append({
            "type": "condition",
            "title": "Excellent Condition",
            "description": "Minimal maintenance expected - ready to drive",
            "severity": "positive",
            "score": 15
        })
        recommendation_score += 15
    elif overall_condition == "Good":
        recommendations.append({
            "type": "condition",
            "title": "Good Condition",
            "description": "Regular maintenance recommended",
            "severity": "positive",
            "score": 10
        })
        recommendation_score += 10
    elif overall_condition == "Fair":
        recommendations.append({
            "type": "condition",
            "title": "Fair Condition",
            "description": "Budget for repairs and maintenance",
            "severity": "neutral",
            "score": 5
        })
        recommendation_score += 5
    else:
        recommendations.append({
            "type": "condition",
            "title": "Poor Condition",
            "description": "Significant repairs needed - proceed with caution",
            "severity": "negative",
            "score": -5
        })
        recommendation_score -= 5
    
    # Age recommendation
    if age < 3:
        recommendations.append({
            "type": "age",
            "title": "Recent Model",
            "description": "Good long-term investment with modern features",
            "severity": "positive",
            "score": 10
        })
        recommendation_score += 10
    elif age < 7:
        recommendations.append({
            "type": "age",
            "title": "Mid-Age Vehicle",
            "description": "Good value for money - depreciation has slowed",
            "severity": "positive",
            "score": 5
        })
        recommendation_score += 5
    elif age < 12:
        recommendations.append({
            "type": "age",
            "title": "Older Vehicle",
            "description": "Depreciation will continue to slow",
            "severity": "neutral",
            "score": 0
        })
    else:
        recommendations.append({
            "type": "age",
            "title": "Vintage Vehicle",
            "description": "Collector potential - value may stabilize",
            "severity": "neutral",
            "score": 0
        })
    
    # Mileage recommendation
    if mileage < 30000:
        recommendations.append({
            "type": "mileage",
            "title": "Low Mileage",
            "description": "Excellent find - below average wear",
            "severity": "positive",
            "score": 10
        })
        recommendation_score += 10
    elif mileage < 60000:
        recommendations.append({
            "type": "mileage",
            "title": "Average Mileage",
            "description": "Reasonable wear for age",
            "severity": "positive",
            "score": 5
        })
        recommendation_score += 5
    elif mileage < 100000:
        recommendations.append({
            "type": "mileage",
            "title": "Above Average Mileage",
            "description": "Check service history carefully",
            "severity": "neutral",
            "score": 0
        })
    else:
        recommendations.append({
            "type": "mileage",
            "title": "High Mileage",
            "description": "Significant wear expected - price accordingly",
            "severity": "negative",
            "score": -5
        })
        recommendation_score -= 5
    
    # Accident history
    if accident_history == "None":
        recommendations.append({
            "type": "accident",
            "title": "Clean History",
            "description": "No accident history - premium value",
            "severity": "positive",
            "score": 10
        })
        recommendation_score += 10
    elif accident_history == "Minor":
        recommendations.append({
            "type": "accident",
            "title": "Minor Accident",
            "description": "Minor damage reported - check repairs",
            "severity": "neutral",
            "score": 0
        })
    else:
        recommendations.append({
            "type": "accident",
            "title": "Major Accident",
            "description": "Significant damage history - inspect thoroughly",
            "severity": "negative",
            "score": -10
        })
        recommendation_score -= 10
    
    # Service history
    if has_service_history:
        recommendations.append({
            "type": "service",
            "title": "Complete Service History",
            "description": "Well-maintained vehicle with records",
            "severity": "positive",
            "score": 5
        })
        recommendation_score += 5
    
    # Determine investment rating
    if recommendation_score >= 40:
        investment_rating = "Strong Buy"
        investment_color = "#22c55e"
        investment_emoji = "🟢"
    elif recommendation_score >= 25:
        investment_rating = "Buy"
        investment_color = "#3b82f6"
        investment_emoji = "🔵"
    elif recommendation_score >= 10:
        investment_rating = "Hold"
        investment_color = "#eab308"
        investment_emoji = "🟡"
    elif recommendation_score >= 0:
        investment_rating = "Caution"
        investment_color = "#f59e0b"
        investment_emoji = "🟠"
    else:
        investment_rating = "Avoid"
        investment_color = "#ef4444"
        investment_emoji = "🔴"
    
    # ─── Build Response ─────────────────────────────────────────────
    
    return {
        "market_value": market_value,
        "condition_assessment": {
            "overall_rating": overall_condition,
            "score": condition_score,
            "max_score": max_score,
            "percentage": condition_percentage,
            "color": condition_color,
            "emoji": condition_emoji,
            "details": condition_details
        },
        "maintenance_cost": maintenance_cost,
        "depreciation_forecast": depreciation_forecast,
        "investment_recommendation": {
            "rating": investment_rating,
            "color": investment_color,
            "emoji": investment_emoji,
            "score": recommendation_score,
            "max_score": 100,
            "recommendations": recommendations
        },
        "assessment_id": str(uuid.uuid4()),
        "generated_at": datetime.now().isoformat()
    }


# ─── Endpoints ──────────────────────────────────────────────────────

@router.post("/assess", response_model=VehicleAssessmentResponse, status_code=status.HTTP_200_OK)
async def assess_vehicle(
    request: VehicleAssessmentRequest,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleAssessmentService = Depends(get_assessment_service),
):
    """
    Perform a comprehensive vehicle assessment.
    
    This endpoint provides a detailed evaluation of a vehicle including:
    - Market value with all factors
    - Condition assessment with detailed breakdown
    - Maintenance cost estimation
    - 5-year depreciation forecast
    - Investment recommendation with detailed reasoning
    
    The assessment is ideal for:
    - Purchase decisions
    - Insurance valuation
    - Financing applications
    - Fleet management
    - Investment analysis
    """
    try:
        # Convert request to dict
        vehicle_data = request.model_dump()
        
        # Perform assessment
        result = perform_vehicle_assessment(vehicle_data)
        
        # Save to database
        assessment_record = {
            "id": result["assessment_id"],
            "user_id": str(current_user.id),
            "make": request.make,
            "model": request.model,
            "year": request.year,
            "mileage": request.mileage,
            "condition": request.condition,
            "location": request.location,
            "market_value": result["market_value"],
            "condition_score": result["condition_assessment"]["score"],
            "condition_rating": result["condition_assessment"]["overall_rating"],
            "maintenance_cost": result["maintenance_cost"],
            "investment_rating": result["investment_recommendation"]["rating"],
            "assessment_data": result,
            "created_at": datetime.now().isoformat()
        }
        
        (
            admin
            .table("vehicle_assessments")
            .insert(assessment_record)
            .execute()
        )
        
        return {
            **result,
            "user_id": str(current_user.id),
            "vehicle_details": {
                "make": request.make,
                "model": request.model,
                "year": request.year,
                "mileage": request.mileage,
                "condition": request.condition,
                "location": request.location
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=BulkAssessmentResponse)
async def bulk_assess_vehicles(
    request: BulkAssessmentRequest,
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Perform comprehensive assessments for multiple vehicles at once.
    """
    try:
        results = []
        total_value = 0
        total_maintenance = 0
        highest_value = 0
        lowest_value = float('inf')
        best_condition = ""
        worst_condition = ""
        
        for vehicle_data in request.vehicles:
            result = perform_vehicle_assessment(vehicle_data)
            
            market_value = result["market_value"]
            maintenance_cost = result["maintenance_cost"]
            condition_rating = result["condition_assessment"]["overall_rating"]
            
            total_value += market_value
            total_maintenance += maintenance_cost
            highest_value = max(highest_value, market_value)
            lowest_value = min(lowest_value, market_value)
            
            # Track best/worst condition
            if not best_condition or condition_rating == "Excellent":
                best_condition = condition_rating
            if not worst_condition or condition_rating == "Poor":
                worst_condition = condition_rating
            
            # Save each assessment
            assessment_record = {
                "id": result["assessment_id"],
                "user_id": str(current_user.id),
                "make": vehicle_data.get("make"),
                "model": vehicle_data.get("model"),
                "year": vehicle_data.get("year"),
                "mileage": vehicle_data.get("mileage", 0),
                "condition": vehicle_data.get("condition", "Good"),
                "location": vehicle_data.get("location", "Other"),
                "market_value": market_value,
                "condition_score": result["condition_assessment"]["score"],
                "condition_rating": condition_rating,
                "maintenance_cost": maintenance_cost,
                "investment_rating": result["investment_recommendation"]["rating"],
                "assessment_data": result,
                "created_at": datetime.now().isoformat()
            }
            
            (
                admin
                .table("vehicle_assessments")
                .insert(assessment_record)
                .execute()
            )
            
            results.append({
                "vehicle": vehicle_data,
                "assessment": result
            })
        
        count = len(results)
        
        return {
            "results": results,
            "summary": {
                "total_vehicles": count,
                "total_value": round(total_value, 2),
                "average_value": round(total_value / count, 2) if count > 0 else 0,
                "average_maintenance": round(total_maintenance / count, 2) if count > 0 else 0,
                "highest_value": round(highest_value, 2) if count > 0 else 0,
                "lowest_value": round(lowest_value, 2) if count > 0 else 0,
                "best_condition": best_condition,
                "worst_condition": worst_condition
            },
            "user_id": str(current_user.id),
            "calculated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=AssessmentComparisonResponse)
async def compare_vehicles(
    request: AssessmentComparisonRequest,
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Compare assessments of multiple vehicles side by side.
    Useful for purchase decisions between multiple options.
    """
    try:
        assessments = []
        best_value_ratio = 0
        best_condition_score = 0
        best_investment_score = -float('inf')
        
        for vehicle_data in request.vehicles:
            result = perform_vehicle_assessment(vehicle_data)
            
            assessment = {
                "vehicle": vehicle_data,
                "assessment": result
            }
            assessments.append(assessment)
            
            # Track best metrics
            condition_score = result["condition_assessment"]["score"]
            investment_score = result["investment_recommendation"]["score"]
            
            if condition_score > best_condition_score:
                best_condition_score = condition_score
            
            if investment_score > best_investment_score:
                best_investment_score = investment_score
        
        return {
            "assessments": assessments,
            "comparison": {
                "total_vehicles": len(assessments),
                "highest_value": max(a["assessment"]["market_value"] for a in assessments) if assessments else 0,
                "lowest_value": min(a["assessment"]["market_value"] for a in assessments) if assessments else 0,
                "best_condition": max(a["assessment"]["condition_assessment"]["overall_rating"] for a in assessments) if assessments else "",
                "best_investment": max(a["assessment"]["investment_recommendation"]["rating"] for a in assessments) if assessments else "",
                "average_condition_score": sum(a["assessment"]["condition_assessment"]["score"] for a in assessments) / len(assessments) if assessments else 0
            },
            "user_id": str(current_user.id),
            "calculated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[AssessmentHistoryResponse])
async def get_assessment_history(
    current_user: UserProfile = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: VehicleAssessmentService = Depends(get_assessment_service),
):
    """
    Get history of vehicle assessments for the current user.
    """
    try:
        result = (
            supabase
            .table("vehicle_assessments")
            .select("*")
            .eq("user_id", str(current_user.id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{assessment_id}", response_model=AssessmentHistoryResponse)
async def get_assessment_by_id(
    assessment_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleAssessmentService = Depends(get_assessment_service),
):
    """
    Get a specific vehicle assessment by ID.
    """
    try:
        result = (
            supabase
            .table("vehicle_assessments")
            .select("*")
            .eq("id", str(assessment_id))
            .eq("user_id", str(current_user.id))
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=AssessmentStats)
async def get_assessment_stats(
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleAssessmentService = Depends(get_assessment_service),
):
    """
    Get statistics about user's vehicle assessments.
    """
    try:
        result = (
            supabase
            .table("vehicle_assessments")
            .select("market_value, condition_score, maintenance_cost, investment_rating, created_at")
            .eq("user_id", str(current_user.id))
            .execute()
        )
        
        data = result.data
        
        if not data:
            return {
                "total_assessments": 0,
                "average_value": 0,
                "average_condition_score": 0,
                "average_maintenance_cost": 0,
                "highest_value": 0,
                "lowest_value": 0,
                "last_30_days": 0,
                "investment_ratings": {
                    "Strong Buy": 0,
                    "Buy": 0,
                    "Hold": 0,
                    "Caution": 0,
                    "Avoid": 0
                },
                "condition_ratings": {
                    "Excellent": 0,
                    "Good": 0,
                    "Fair": 0,
                    "Poor": 0
                }
            }
        
        total = len(data)
        values = [v.get("market_value", 0) for v in data if v.get("market_value")]
        condition_scores = [v.get("condition_score", 0) for v in data if v.get("condition_score")]
        maintenance_costs = [v.get("maintenance_cost", 0) for v in data if v.get("maintenance_cost")]
        
        # Count last 30 days
        thirty_days_ago = datetime.now().timestamp() - (30 * 24 * 60 * 60)
        last_30_days = sum(1 for v in data if v.get("created_at") and 
                          datetime.fromisoformat(v["created_at"]).timestamp() > thirty_days_ago)
        
        # Count investment ratings
        investment_ratings = {
            "Strong Buy": 0,
            "Buy": 0,
            "Hold": 0,
            "Caution": 0,
            "Avoid": 0
        }
        for v in data:
            rating = v.get("investment_rating")
            if rating in investment_ratings:
                investment_ratings[rating] += 1
        
        # Count condition ratings
        condition_ratings = {
            "Excellent": 0,
            "Good": 0,
            "Fair": 0,
            "Poor": 0
        }
        for v in data:
            rating = v.get("condition_rating")
            if rating in condition_ratings:
                condition_ratings[rating] += 1
        
        return {
            "total_assessments": total,
            "average_value": round(sum(values) / len(values), 2) if values else 0,
            "average_condition_score": round(sum(condition_scores) / len(condition_scores), 2) if condition_scores else 0,
            "average_maintenance_cost": round(sum(maintenance_costs) / len(maintenance_costs), 2) if maintenance_costs else 0,
            "highest_value": max(values) if values else 0,
            "lowest_value": min(values) if values else 0,
            "last_30_days": last_30_days,
            "investment_ratings": investment_ratings,
            "condition_ratings": condition_ratings
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleAssessmentService = Depends(get_assessment_service),
):
    """
    Delete a vehicle assessment from history.
    """
    try:
        # Check ownership
        check = (
            supabase
            .table("vehicle_assessments")
            .select("user_id")
            .eq("id", str(assessment_id))
            .execute()
        )
        
        if not check.data:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        if check.data[0]["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to delete this assessment")
        
        (
            admin
            .table("vehicle_assessments")
            .delete()
            .eq("id", str(assessment_id))
            .execute()
        )
        
        return None
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/all", status_code=status.HTTP_204_NO_CONTENT)
async def clear_assessment_history(
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleAssessmentService = Depends(get_assessment_service),
):
    """
    Clear all vehicle assessment history for the current user.
    """
    try:
        (
            admin
            .table("vehicle_assessments")
            .delete()
            .eq("user_id", str(current_user.id))
            .execute()
        )
        return None
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Admin Endpoints ──────────────────────────────────────────────────

@router.get("/admin/all", response_model=List[AssessmentHistoryResponse])
async def admin_list_all_assessments(
    current_admin: UserProfile = Depends(get_current_admin_user),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: VehicleAssessmentService = Depends(get_assessment_service),
):
    """
    List all vehicle assessments across all users (Admin only).
    """
    try:
        result = (
            supabase
            .table("vehicle_assessments")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/stats", response_model=dict)
async def admin_get_assessment_stats(
    current_admin: UserProfile = Depends(get_current_admin_user),
    service: VehicleAssessmentService = Depends(get_assessment_service),
):
    """
    Get global vehicle assessment statistics (Admin only).
    """
    try:
        result = (
            supabase
            .table("vehicle_assessments")
            .select("market_value, condition_score, investment_rating, user_id")
            .execute()
        )
        
        data = result.data
        
        if not data:
            return {
                "total_assessments": 0,
                "average_value": 0,
                "average_condition_score": 0,
                "total_users": 0,
                "investment_ratings": {
                    "Strong Buy": 0,
                    "Buy": 0,
                    "Hold": 0,
                    "Caution": 0,
                    "Avoid": 0
                }
            }
        
        total = len(data)
        values = [v.get("market_value", 0) for v in data if v.get("market_value")]
        condition_scores = [v.get("condition_score", 0) for v in data if v.get("condition_score")]
        
        # Get unique users
        users = set(v.get("user_id") for v in data if v.get("user_id"))
        
        # Count investment ratings
        investment_ratings = {
            "Strong Buy": 0,
            "Buy": 0,
            "Hold": 0,
            "Caution": 0,
            "Avoid": 0
        }
        for v in data:
            rating = v.get("investment_rating")
            if rating in investment_ratings:
                investment_ratings[rating] += 1
        
        return {
            "total_assessments": total,
            "average_value": round(sum(values) / len(values), 2) if values else 0,
            "average_condition_score": round(sum(condition_scores) / len(condition_scores), 2) if condition_scores else 0,
            "total_users": len(users),
            "investment_ratings": investment_ratings
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
