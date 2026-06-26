"""
Assessment Routes - FastAPI Version
Vehicle assessment, damage analysis, and risk evaluation
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging

from app.core.database import supabase
from app.core.dependencies import get_current_user
from app.services.assessment import run_assessment
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assessments", tags=["Assessments"])


# ─── Pydantic Models ──────────────────────────────────────────

class VehicleAssessmentData(BaseModel):
    """Vehicle assessment data model"""
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: Optional[int] = Field(None, description="Vehicle year")
    vin: Optional[str] = Field(None, description="Vehicle VIN")
    registration: Optional[str] = Field(None, description="Vehicle registration")
    mileage: Optional[int] = Field(None, description="Vehicle mileage")
    condition: Optional[str] = Field(None, description="Vehicle condition")
    accident_history: Optional[str] = Field(None, description="Accident history")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    engine_cc: Optional[int] = Field(None, description="Engine capacity")
    color: Optional[str] = Field(None, description="Vehicle color")
    location: Optional[str] = Field(None, description="Vehicle location")
    
    @validator('vin')
    def validate_vin(cls, v):
        if v and len(v) != 17:
            raise ValueError('VIN must be 17 characters')
        return v.upper() if v else v


class AssessmentRequest(BaseModel):
    """Assessment request model"""
    assessment_type: str = Field(..., description="Assessment type")
    vehicle: VehicleAssessmentData = Field(..., description="Vehicle data")
    notes: Optional[str] = Field(None, description="Additional notes")
    images: Optional[List[str]] = Field(None, description="List of image URLs")
    documents: Optional[List[str]] = Field(None, description="List of document URLs")


class AssessmentResponse(BaseModel):
    """Assessment response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None
    assessment_id: Optional[str] = None
    timestamp: Optional[str] = None


# ─── Assessment Types ──────────────────────────────────────────

ASSESSMENT_TYPES = {
    "damage": "Damage Assessment",
    "risk": "Risk Assessment",
    "condition": "Condition Assessment",
    "value": "Value Assessment",
    "safety": "Safety Assessment",
    "theft": "Theft Risk Assessment",
    "insurance": "Insurance Risk Assessment",
    "comprehensive": "Comprehensive Assessment"
}


# ─── Helper Functions ──────────────────────────────────────────

def generate_assessment_id() -> str:
    """Generate a unique assessment ID."""
    return f"ASS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def validate_assessment_type(assessment_type: str) -> bool:
    """Validate assessment type."""
    return assessment_type in ASSESSMENT_TYPES


def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()


# ─── Routes ──────────────────────────────────────────────────

@router.post("/create", response_model=AssessmentResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def create_assessment(
    request: AssessmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new vehicle assessment.
    
    **Request Body:**
    - `assessment_type`: Type of assessment (damage, risk, condition, value, safety, theft, insurance, comprehensive)
    - `vehicle`: Vehicle data (make, model, year, vin, etc.)
    - `notes`: Additional notes
    - `images`: List of image URLs
    - `documents`: List of document URLs
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Assessment results
    - `assessment_id`: Unique assessment ID
    - `message`: Status message
    - `error`: Error message if unsuccessful
    """
    try:
        # Validate assessment type
        if not validate_assessment_type(request.assessment_type):
            return AssessmentResponse(
                success=False,
                error=f"Invalid assessment type. Must be one of: {', '.join(ASSESSMENT_TYPES.keys())}"
            )
        
        # Get vehicle data
        vehicle = request.vehicle.dict()
        
        # Generate assessment ID
        assessment_id = generate_assessment_id()
        
        # Prepare assessment data
        assessment_data = {
            "user_id": current_user.get("id"),
            "assessment_type": request.assessment_type,
            "assessment_id": assessment_id,
            "vehicle": vehicle,
            "notes": request.notes,
            "images": request.images or [],
            "documents": request.documents or [],
            "status": "processing",
            "created_at": format_timestamp()
        }
        
        # Run assessment
        result = run_assessment(request.assessment_type, **assessment_data)
        
        # Save to Supabase
        save_data = {
            "user_id": current_user.get("id"),
            "assessment_type": request.assessment_type,
            "assessment_id": assessment_id,
            "vehicle_data": vehicle,
            "result": result,
            "status": "completed",
            "created_at": format_timestamp(),
            "updated_at": format_timestamp()
        }
        
        # Save to database
        db_response = supabase.table("assessments").insert(save_data).execute()
        
        if db_response.data:
            assessment_id = db_response.data[0].get("id")
            result["id"] = assessment_id
        
        return AssessmentResponse(
            success=True,
            data=result,
            assessment_id=assessment_id,
            message=f"{ASSESSMENT_TYPES[request.assessment_type]} completed successfully",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Create assessment error: {str(e)}", exc_info=True)
        return AssessmentResponse(
            success=False,
            error=str(e)
        )


@router.get("/{assessment_id}", response_model=AssessmentResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_assessment(
    assessment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get assessment by ID.
    
    **Path Parameter:**
    - `assessment_id`: Assessment ID to retrieve
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Assessment data
    - `error`: Error message if unsuccessful
    """
    try:
        # Get assessment from database
        response = supabase.table("assessments") \
            .select("*") \
            .eq("assessment_id", assessment_id) \
            .execute()
        
        if not response.data:
            return AssessmentResponse(
                success=False,
                error="Assessment not found"
            )
        
        assessment = response.data[0]
        
        # Check permissions
        if assessment.get("user_id") != current_user.get("id") and current_user.get("role") not in ["admin", "super_admin"]:
            return AssessmentResponse(
                success=False,
                error="Access denied"
            )
        
        return AssessmentResponse(
            success=True,
            data=assessment,
            assessment_id=assessment.get("assessment_id"),
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get assessment error: {str(e)}", exc_info=True)
        return AssessmentResponse(
            success=False,
            error=str(e)
        )


@router.get("/", response_model=AssessmentResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def list_assessments(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    assessment_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    List user assessments.
    
    **Query Parameters:**
    - `limit`: Number of results to return (default: 50, max: 100)
    - `offset`: Number of results to skip (default: 0)
    - `assessment_type`: Filter by assessment type
    - `status`: Filter by status
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of assessments
    - `count`: Total count
    - `error`: Error message if unsuccessful
    """
    try:
        # Build query
        query = supabase.table("assessments") \
            .select("*") \
            .eq("user_id", current_user.get("id"))
        
        # Apply filters
        if assessment_type:
            query = query.eq("assessment_type", assessment_type)
        if status:
            query = query.eq("status", status)
        
        # Apply pagination
        query = query.order("created_at", desc=True) \
            .range(offset, offset + limit - 1)
        
        response = query.execute()
        
        return AssessmentResponse(
            success=True,
            data={
                "assessments": response.data,
                "count": len(response.data),
                "limit": limit,
                "offset": offset
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"List assessments error: {str(e)}", exc_info=True)
        return AssessmentResponse(
            success=False,
            error=str(e)
        )


@router.put("/{assessment_id}", response_model=AssessmentResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def update_assessment(
    assessment_id: str,
    update_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Update assessment.
    
    **Path Parameter:**
    - `assessment_id`: Assessment ID to update
    
    **Request Body:**
    - Any fields to update
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Updated assessment data
    - `message`: Status message
    - `error`: Error message if unsuccessful
    """
    try:
        # Get assessment
        response = supabase.table("assessments") \
            .select("*") \
            .eq("assessment_id", assessment_id) \
            .execute()
        
        if not response.data:
            return AssessmentResponse(
                success=False,
                error="Assessment not found"
            )
        
        assessment = response.data[0]
        
        # Check permissions
        if assessment.get("user_id") != current_user.get("id") and current_user.get("role") not in ["admin", "super_admin"]:
            return AssessmentResponse(
                success=False,
                error="Access denied"
            )
        
        # Update assessment
        update_data["updated_at"] = format_timestamp()
        
        result = supabase.table("assessments") \
            .update(update_data) \
            .eq("assessment_id", assessment_id) \
            .execute()
        
        return AssessmentResponse(
            success=True,
            data=result.data[0] if result.data else None,
            message="Assessment updated successfully",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Update assessment error: {str(e)}", exc_info=True)
        return AssessmentResponse(
            success=False,
            error=str(e)
        )


@router.delete("/{assessment_id}", response_model=AssessmentResponse)
@rate_limit(limit=5, per=60)
@require_auth
@log_request
@handle_errors
async def delete_assessment(
    assessment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete assessment.
    
    **Path Parameter:**
    - `assessment_id`: Assessment ID to delete
    
    **Response:**
    - `success`: Boolean indicating success
    - `message`: Status message
    - `error`: Error message if unsuccessful
    """
    try:
        # Get assessment
        response = supabase.table("assessments") \
            .select("*") \
            .eq("assessment_id", assessment_id) \
            .execute()
        
        if not response.data:
            return AssessmentResponse(
                success=False,
                error="Assessment not found"
            )
        
        assessment = response.data[0]
        
        # Check permissions
        if assessment.get("user_id") != current_user.get("id") and current_user.get("role") not in ["admin", "super_admin"]:
            return AssessmentResponse(
                success=False,
                error="Access denied"
            )
        
        # Delete assessment
        supabase.table("assessments") \
            .delete() \
            .eq("assessment_id", assessment_id) \
            .execute()
        
        return AssessmentResponse(
            success=True,
            message="Assessment deleted successfully",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Delete assessment error: {str(e)}", exc_info=True)
        return AssessmentResponse(
            success=False,
            error=str(e)
        )


@router.get("/types", response_model=AssessmentResponse)
@rate_limit(limit=30, per=60)
@log_request
@handle_errors
async def get_assessment_types():
    """
    Get available assessment types.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of assessment types with descriptions
    """
    return AssessmentResponse(
        success=True,
        data={
            "types": [
                {"key": "damage", "name": "Damage Assessment", "description": "Assess vehicle damage and repair costs"},
                {"key": "risk", "name": "Risk Assessment", "description": "Evaluate vehicle risk factors"},
                {"key": "condition", "name": "Condition Assessment", "description": "Assess overall vehicle condition"},
                {"key": "value", "name": "Value Assessment", "description": "Assess vehicle market value"},
                {"key": "safety", "name": "Safety Assessment", "description": "Evaluate vehicle safety features"},
                {"key": "theft", "name": "Theft Risk Assessment", "description": "Assess theft risk factors"},
                {"key": "insurance", "name": "Insurance Risk Assessment", "description": "Evaluate insurance risk factors"},
                {"key": "comprehensive", "name": "Comprehensive Assessment", "description": "Full vehicle assessment"}
            ]
        },
        timestamp=format_timestamp()
    )


@router.post("/quick", response_model=AssessmentResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def quick_assessment(
    vehicle: VehicleAssessmentData,
    current_user: dict = Depends(get_current_user)
):
    """
    Quick vehicle assessment.
    
    **Request Body:**
    - Vehicle data (make, model, year, etc.)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Quick assessment results
    """
    try:
        # Run quick assessment
        result = {
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "condition": vehicle.condition or "Unknown",
            "estimated_value": "To be determined",
            "risk_level": "Medium",
            "assessment_date": format_timestamp()
        }
        
        return AssessmentResponse(
            success=True,
            data=result,
            message="Quick assessment completed",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Quick assessment error: {str(e)}", exc_info=True)
        return AssessmentResponse(
            success=False,
            error=str(e)
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
