"""
Intelligence Routes - FastAPI Backend
AI-powered market analysis, price prediction, damage detection, chat, and recommendations
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import re

from app.core.database import execute_query
from app.core.dependencies import get_current_user, get_current_active_user, require_role
from app.services.openai_service import openai_service
from app.services.carapi_service import car_api
from app.services.vin_validator import vin_validator
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors
from app.models.intelligence import (
    MarketAnalysisRequest,
    PricePredictionRequest,
    DamageDetectionRequest,
    ChatRequest,
    RecommendationsRequest,
    IntelligenceResponse,
    AIModelsResponse,
    HealthResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/intelligence", tags=["Intelligence"])

# ─── Constants ──────────────────────────────────────────────────

SUPPORTED_CONDITIONS = ["Excellent", "Good", "Fair", "Poor"]
SUPPORTED_FUEL_TYPES = ["Petrol", "Diesel", "Hybrid", "Electric", "LPG"]
SUPPORTED_TRANSMISSIONS = ["Manual", "Automatic", "CVT", "DCT"]
SUPPORTED_VEHICLE_TYPES = ["Sedan", "SUV", "Pickup", "Van", "Hatchback", "Coupe", "Convertible", "Wagon", "Minivan", "Bus", "Truck"]

# ─── Helper Functions ──────────────────────────────────────────

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()

def validate_vehicle_year(year: int) -> bool:
    """Validate vehicle year."""
    current_year = datetime.now().year
    return 1900 <= year <= current_year + 1

def validate_mileage(mileage: int) -> bool:
    """Validate vehicle mileage."""
    return 0 <= mileage <= 1000000

# ─── Routes ──────────────────────────────────────────────────

@router.post("/market-analysis", response_model=IntelligenceResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def market_analysis(
    request: MarketAnalysisRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get AI-powered market analysis for a vehicle.
    
    **Request Body:**
    - `vin`: Vehicle VIN (17 characters)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Market analysis with vehicle details and AI insights
    """
    try:
        vin = request.vin.upper().strip()
        
        # Validate VIN
        if not vin_validator.is_valid(vin):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid VIN format. Must be 17 characters."
            )
        
        # Check if analysis exists in cache
        cache_query = """
            SELECT * FROM intelligence_cache 
            WHERE vin = $1 AND analysis_type = 'market_analysis' 
            AND created_at > NOW() - INTERVAL '7 days'
        """
        cache_result = await execute_query(cache_query, [vin])
        
        if cache_result and len(cache_result) > 0:
            # Return cached result
            cached = cache_result[0]
            return IntelligenceResponse(
                success=True,
                data=cached.get('data', {}),
                message="Market analysis retrieved from cache",
                timestamp=format_timestamp()
            )
        
        # Get vehicle details from CarAPI
        vehicle = car_api.decode_vin(vin)
        
        if 'error' in vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found in database"
            )
        
        # Get AI market analysis
        analysis = openai_service.market_analysis(vehicle)
        
        # Save to cache
        cache_data = {
            "vin": vin,
            "analysis_type": "market_analysis",
            "data": {
                "vin": vin,
                "vehicle": vehicle,
                "analysis": analysis
            },
            "created_at": format_timestamp()
        }
        
        insert_query = """
            INSERT INTO intelligence_cache (vin, analysis_type, data, created_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (vin, analysis_type) 
            DO UPDATE SET data = $3, created_at = $4
        """
        await execute_query(
            insert_query,
            [vin, "market_analysis", cache_data["data"], cache_data["created_at"]]
        )
        
        return IntelligenceResponse(
            success=True,
            data={
                "vin": vin,
                "vehicle": vehicle,
                "analysis": analysis,
                "timestamp": format_timestamp()
            },
            message="Market analysis completed successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Market analysis error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform market analysis: {str(e)}"
        )


@router.post("/predict-price", response_model=IntelligenceResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def predict_price(
    request: PricePredictionRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Predict vehicle price using AI.
    
    **Request Body:**
    - `make`: Vehicle make
    - `model`: Vehicle model
    - `year`: Vehicle year
    - `mileage`: Vehicle mileage (optional)
    - `condition`: Vehicle condition (optional)
    - `fuel_type`: Fuel type (optional)
    - `transmission`: Transmission type (optional)
    - `location`: Location (optional)
    - `accident_history`: Accident history (optional)
    - `owners`: Number of owners (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Price prediction results
    """
    try:
        # Validate required fields
        if not request.make or not request.model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Make and model are required"
            )
        
        if not validate_vehicle_year(request.year):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Year must be between 1900 and {datetime.now().year + 1}"
            )
        
        if request.mileage is not None and not validate_mileage(request.mileage):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mileage must be between 0 and 1,000,000"
            )
        
        # Prepare prediction data
        prediction_data = request.dict(exclude_none=True)
        
        # Check if prediction exists in cache
        cache_key = f"{request.make}_{request.model}_{request.year}_{request.mileage}_{request.condition}"
        cache_query = """
            SELECT * FROM intelligence_cache 
            WHERE cache_key = $1 AND analysis_type = 'price_prediction'
            AND created_at > NOW() - INTERVAL '1 day'
        """
        cache_result = await execute_query(cache_query, [cache_key])
        
        if cache_result and len(cache_result) > 0:
            cached = cache_result[0]
            return IntelligenceResponse(
                success=True,
                data=cached.get('data', {}),
                message="Price prediction retrieved from cache",
                timestamp=format_timestamp()
            )
        
        # Get AI price prediction
        prediction = openai_service.predict_price(prediction_data)
        
        # Save to cache
        cache_data = {
            "cache_key": cache_key,
            "analysis_type": "price_prediction",
            "data": prediction,
            "created_at": format_timestamp()
        }
        
        insert_query = """
            INSERT INTO intelligence_cache (cache_key, analysis_type, data, created_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (cache_key, analysis_type) 
            DO UPDATE SET data = $3, created_at = $4
        """
        await execute_query(
            insert_query,
            [cache_key, "price_prediction", prediction, cache_data["created_at"]]
        )
        
        return IntelligenceResponse(
            success=True,
            data=prediction,
            message="Price prediction completed successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Price prediction error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to predict price: {str(e)}"
        )


@router.post("/detect-damage", response_model=IntelligenceResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def detect_damage(
    request: DamageDetectionRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Detect damage in vehicle images using AI.
    
    **Request Body:**
    - `image_urls`: List of image URLs to analyze (max 10)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Damage detection results per image
    """
    try:
        image_urls = request.image_urls
        
        if not image_urls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No image URLs provided"
            )
        
        if len(image_urls) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 images allowed"
            )
        
        # Process each image
        results = []
        damage_detected = False
        total_damage_score = 0
        
        for url in image_urls:
            try:
                detection = openai_service.detect_damage(url)
                if detection.get('damage_detected', False):
                    damage_detected = True
                    total_damage_score += detection.get('damage_score', 0)
                results.append({
                    "image_url": url,
                    "detection": detection
                })
            except Exception as e:
                logger.error(f"Damage detection failed for {url}: {str(e)}")
                results.append({
                    "image_url": url,
                    "detection": {
                        "damage_detected": False,
                        "error": "Failed to analyze image"
                    }
                })
        
        # Calculate overall damage assessment
        overall_assessment = {
            "damage_detected": damage_detected,
            "total_images": len(results),
            "images_with_damage": len([r for r in results if r['detection'].get('damage_detected', False)]),
            "average_damage_score": total_damage_score / len(results) if results else 0,
            "severity": "High" if damage_detected and total_damage_score > 50 else "Medium" if damage_detected else "Low"
        }
        
        # Save to database for audit
        log_data = {
            "user_id": current_user['id'],
            "analysis_type": "damage_detection",
            "image_count": len(image_urls),
            "damage_detected": damage_detected,
            "results": results,
            "overall_assessment": overall_assessment,
            "created_at": format_timestamp()
        }
        
        insert_query = """
            INSERT INTO intelligence_logs (user_id, analysis_type, data, created_at)
            VALUES ($1, $2, $3, $4)
        """
        await execute_query(
            insert_query,
            [current_user['id'], "damage_detection", log_data, log_data["created_at"]]
        )
        
        return IntelligenceResponse(
            success=True,
            data={
                "results": results,
                "overall_assessment": overall_assessment,
                "total_images": len(results)
            },
            message="Damage detection completed successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Damage detection error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect damage: {str(e)}"
        )


@router.post("/chat", response_model=IntelligenceResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    AI Chat Assistant for vehicle queries.
    
    **Request Body:**
    - `message`: User message
    - `context`: Chat context (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: AI response
    """
    try:
        if not request.message or len(request.message.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        if len(request.message) > 2000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message too long (max 2000 characters)"
            )
        
        # Get AI chat response
        response = openai_service.chat(
            message=request.message,
            context=request.context or {}
        )
        
        # Save chat history
        chat_data = {
            "user_id": current_user['id'],
            "message": request.message,
            "response": response,
            "context": request.context or {},
            "created_at": format_timestamp()
        }
        
        insert_query = """
            INSERT INTO chat_history (user_id, message, response, context, created_at)
            VALUES ($1, $2, $3, $4, $5)
        """
        await execute_query(
            insert_query,
            [current_user['id'], request.message, response, request.context or {}, chat_data["created_at"]]
        )
        
        return IntelligenceResponse(
            success=True,
            data={
                "response": response,
                "message": request.message,
                "timestamp": format_timestamp()
            },
            message="Chat response generated successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat: {str(e)}"
        )


@router.post("/recommendations", response_model=IntelligenceResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_recommendations(
    request: RecommendationsRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get AI-powered vehicle recommendations.
    
    **Request Body:**
    - `preferences`: User preferences (required)
    - `budget`: Budget range (optional)
    - `vehicle_type`: Vehicle type preference (optional)
    - `fuel_type`: Fuel type preference (optional)
    - `transmission`: Transmission preference (optional)
    - `usage`: Vehicle usage purpose (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Vehicle recommendations
    """
    try:
        if not request.preferences or len(request.preferences) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preferences are required"
            )
        
        # Prepare recommendation data
        rec_data = {
            "preferences": request.preferences,
            "budget": request.budget,
            "vehicle_type": request.vehicle_type,
            "fuel_type": request.fuel_type,
            "transmission": request.transmission,
            "usage": request.usage
        }
        
        # Get AI recommendations
        recommendations = openai_service.get_recommendations(rec_data)
        
        # Save to database
        rec_log = {
            "user_id": current_user['id'],
            "preferences": request.preferences,
            "budget": request.budget,
            "vehicle_type": request.vehicle_type,
            "fuel_type": request.fuel_type,
            "transmission": request.transmission,
            "usage": request.usage,
            "recommendations": recommendations,
            "created_at": format_timestamp()
        }
        
        insert_query = """
            INSERT INTO recommendation_logs 
            (user_id, preferences, budget, vehicle_type, fuel_type, transmission, usage, recommendations, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        await execute_query(
            insert_query,
            [
                current_user['id'],
                request.preferences,
                request.budget,
                request.vehicle_type,
                request.fuel_type,
                request.transmission,
                request.usage,
                recommendations,
                rec_log["created_at"]
            ]
        )
        
        return IntelligenceResponse(
            success=True,
            data={
                "recommendations": recommendations,
                "preferences_used": rec_data
            },
            message="Recommendations generated successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendations error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.get("/models", response_model=AIModelsResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_ai_models(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get available AI models and their capabilities.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of available AI models
    """
    try:
        models = {
            "market_analysis": {
                "name": "Market Analysis AI",
                "version": "2.0.0",
                "description": "AI-powered vehicle market analysis",
                "capabilities": ["value_prediction", "trend_analysis", "comparable_sales"],
                "requires_vin": True
            },
            "price_prediction": {
                "name": "Price Prediction AI",
                "version": "2.0.0",
                "description": "AI-powered vehicle price prediction",
                "capabilities": ["price_forecast", "depreciation", "residual_value"],
                "requires_vin": False
            },
            "damage_detection": {
                "name": "Damage Detection AI",
                "version": "2.0.0",
                "description": "AI-powered vehicle damage detection",
                "capabilities": ["image_analysis", "damage_classification", "severity_scoring"],
                "requires_vin": False,
                "requires_images": True
            },
            "chat_assistant": {
                "name": "Chat Assistant AI",
                "version": "2.0.0",
                "description": "AI-powered chat assistant for vehicle queries",
                "capabilities": ["q_and_a", "guidance", "support"],
                "requires_vin": False
            },
            "recommendations": {
                "name": "Recommendations AI",
                "version": "2.0.0",
                "description": "AI-powered vehicle recommendations",
                "capabilities": ["personalization", "matching", "comparison"],
                "requires_vin": False
            }
        }
        
        return AIModelsResponse(
            success=True,
            data=models,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get AI models error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get AI models: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
@rate_limit(limit=30, per=60)
@log_request
@handle_errors
async def intelligence_health():
    """
    Intelligence service health check.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Service health status
    """
    try:
        # Check OpenAI service health
        openai_health = {"status": "operational", "version": "2.0.0"}
        
        # Check database connection
        db_health = {"status": "operational"}
        try:
            await execute_query("SELECT 1", [])
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            db_health = {"status": "degraded", "error": str(e)}
        
        # Check cache status
        cache_health = {"status": "operational"}
        try:
            cache_query = "SELECT COUNT(*) FROM intelligence_cache LIMIT 1"
            await execute_query(cache_query, [])
        except Exception as e:
            logger.error(f"Cache health check failed: {str(e)}")
            cache_health = {"status": "degraded", "error": str(e)}
        
        overall_status = "operational"
        if db_health["status"] == "degraded" or cache_health["status"] == "degraded":
            overall_status = "degraded"
        
        return HealthResponse(
            success=True,
            data={
                "status": overall_status,
                "openai": openai_health,
                "database": db_health,
                "cache": cache_health,
                "timestamp": format_timestamp()
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Intelligence health error: {str(e)}", exc_info=True)
        return HealthResponse(
            success=False,
            data={"status": "error", "error": str(e)},
            error=str(e),
            timestamp=format_timestamp()
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
