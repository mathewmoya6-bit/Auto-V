"""
Intelligence Routes - FastAPI Version
AI-powered market analysis, price prediction, damage detection, chat, and recommendations
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.core.dependencies import get_current_user
from app.services.openai_service import openai_service
from app.services.carapi_service import car_api
from app.services.vin_validator import vin_validator
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligence", tags=["Intelligence"])


# ─── Pydantic Models ──────────────────────────────────────────

class MarketAnalysisRequest(BaseModel):
    """Market analysis request model"""
    vin: str = Field(..., description="Vehicle VIN")
    
    @validator('vin')
    def validate_vin(cls, v):
        v = v.upper().strip()
        if len(v) != 17:
            raise ValueError('VIN must be 17 characters')
        return v


class PricePredictionRequest(BaseModel):
    """Price prediction request model"""
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: int = Field(..., description="Vehicle year")
    mileage: Optional[int] = Field(None, description="Vehicle mileage")
    condition: Optional[str] = Field(None, description="Vehicle condition")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    location: Optional[str] = Field(None, description="Location")
    accident_history: Optional[str] = Field(None, description="Accident history")
    owners: Optional[int] = Field(None, description="Number of owners")


class DamageDetectionRequest(BaseModel):
    """Damage detection request model"""
    image_urls: List[str] = Field(..., description="List of image URLs to analyze")


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., description="User message")
    context: Optional[Dict[str, Any]] = Field(None, description="Chat context")


class RecommendationsRequest(BaseModel):
    """Recommendations request model"""
    preferences: Dict[str, Any] = Field(..., description="User preferences")
    budget: Optional[float] = Field(None, description="Budget range")
    vehicle_type: Optional[str] = Field(None, description="Vehicle type preference")
    fuel_type: Optional[str] = Field(None, description="Fuel type preference")
    transmission: Optional[str] = Field(None, description="Transmission preference")
    usage: Optional[str] = Field(None, description="Vehicle usage purpose")


class IntelligenceResponse(BaseModel):
    """Standard intelligence response"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


# ─── Helper Functions ──────────────────────────────────────────

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()


# ─── Routes ──────────────────────────────────────────────────

@router.post("/market-analysis", response_model=IntelligenceResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def market_analysis(
    request: MarketAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI-powered market analysis for a vehicle.
    
    **Request Body:**
    - `vin`: Vehicle VIN
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Market analysis with vehicle details and AI insights
    - `error`: Error message if unsuccessful
    """
    try:
        vin = request.vin.upper().strip()
        
        # Validate VIN
        if not vin_validator.is_valid(vin):
            return IntelligenceResponse(
                success=False,
                error="Invalid VIN format"
            )
        
        # Get vehicle details from CarAPI
        vehicle = car_api.decode_vin(vin)
        
        if 'error' in vehicle:
            return IntelligenceResponse(
                success=False,
                error="Vehicle not found in database"
            )
        
        # Get AI market analysis
        analysis = openai_service.market_analysis(vehicle)
        
        return IntelligenceResponse(
            success=True,
            data={
                "vin": vin,
                "vehicle": vehicle,
                "analysis": analysis,
                "timestamp": format_timestamp()
            }
        )
        
    except Exception as e:
        logger.error(f"Market analysis error: {str(e)}", exc_info=True)
        return IntelligenceResponse(
            success=False,
            error=str(e)
        )


@router.post("/predict-price", response_model=IntelligenceResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def predict_price(
    request: PricePredictionRequest,
    current_user: dict = Depends(get_current_user)
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
    - `error`: Error message if unsuccessful
    """
    try:
        # Prepare prediction data
        prediction_data = request.dict(exclude_none=True)
        
        # Get AI price prediction
        prediction = openai_service.predict_price(prediction_data)
        
        return IntelligenceResponse(
            success=True,
            data=prediction,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Price prediction error: {str(e)}", exc_info=True)
        return IntelligenceResponse(
            success=False,
            error=str(e)
        )


@router.post("/detect-damage", response_model=IntelligenceResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def detect_damage(
    request: DamageDetectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Detect damage in vehicle images using AI.
    
    **Request Body:**
    - `image_urls`: List of image URLs to analyze
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Damage detection results per image
    - `error`: Error message if unsuccessful
    """
    try:
        image_urls = request.image_urls
        
        if not image_urls:
            return IntelligenceResponse(
                success=False,
                error="No image URLs provided"
            )
        
        # Process each image
        results = []
        damage_detected = False
        
        for url in image_urls:
            detection = openai_service.detect_damage(url)
            if detection.get('damage_detected', False):
                damage_detected = True
            results.append({
                "image_url": url,
                "detection": detection
            })
        
        return IntelligenceResponse(
            success=True,
            data={
                "results": results,
                "total_images": len(results),
                "damage_detected": damage_detected
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Damage detection error: {str(e)}", exc_info=True)
        return IntelligenceResponse(
            success=False,
            error=str(e)
        )


@router.post("/chat", response_model=IntelligenceResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    AI Chat Assistant for vehicle queries.
    
    **Request Body:**
    - `message`: User message
    - `context`: Chat context (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: AI response
    - `error`: Error message if unsuccessful
    """
    try:
        # Get AI chat response
        response = openai_service.chat(
            message=request.message,
            context=request.context or {}
        )
        
        return IntelligenceResponse(
            success=True,
            data={
                "response": response,
                "message": request.message,
                "timestamp": format_timestamp()
            }
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        return IntelligenceResponse(
            success=False,
            error=str(e)
        )


@router.post("/recommendations", response_model=IntelligenceResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_recommendations(
    request: RecommendationsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI-powered vehicle recommendations.
    
    **Request Body:**
    - `preferences`: User preferences
    - `budget`: Budget range (optional)
    - `vehicle_type`: Vehicle type preference (optional)
    - `fuel_type`: Fuel type preference (optional)
    - `transmission`: Transmission preference (optional)
    - `usage`: Vehicle usage purpose (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Vehicle recommendations
    - `error`: Error message if unsuccessful
    """
    try:
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
        
        return IntelligenceResponse(
            success=True,
            data=recommendations,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Recommendations error: {str(e)}", exc_info=True)
        return IntelligenceResponse(
            success=False,
            error=str(e)
        )


@router.get("/models", response_model=IntelligenceResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_ai_models(
    current_user: dict = Depends(get_current_user)
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
                "capabilities": ["value_prediction", "trend_analysis", "comparable_sales"]
            },
            "price_prediction": {
                "name": "Price Prediction AI",
                "version": "2.0.0",
                "description": "AI-powered vehicle price prediction",
                "capabilities": ["price_forecast", "depreciation", "residual_value"]
            },
            "damage_detection": {
                "name": "Damage Detection AI",
                "version": "2.0.0",
                "description": "AI-powered vehicle damage detection",
                "capabilities": ["image_analysis", "damage_classification", "severity_scoring"]
            },
            "chat_assistant": {
                "name": "Chat Assistant AI",
                "version": "2.0.0",
                "description": "AI-powered chat assistant for vehicle queries",
                "capabilities": ["q_and_a", "guidance", "support"]
            },
            "recommendations": {
                "name": "Recommendations AI",
                "version": "2.0.0",
                "description": "AI-powered vehicle recommendations",
                "capabilities": ["personalization", "matching", "comparison"]
            }
        }
        
        return IntelligenceResponse(
            success=True,
            data=models,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get AI models error: {str(e)}", exc_info=True)
        return IntelligenceResponse(
            success=False,
            error=str(e)
        )


@router.get("/health", response_model=IntelligenceResponse)
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
        openai_health = openai_service.health_check() if hasattr(openai_service, 'health_check') else {"status": "unknown"}
        
        return IntelligenceResponse(
            success=True,
            data={
                "status": "operational",
                "openai": openai_health,
                "timestamp": format_timestamp()
            }
        )
        
    except Exception as e:
        logger.error(f"Intelligence health error: {str(e)}", exc_info=True)
        return IntelligenceResponse(
            success=False,
            error=str(e)
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
