"""
Inspection Routes - FastAPI Version
Vehicle inspection creation, retrieval, and quick estimates
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging

from app.core.database import supabase
from app.core.dependencies import get_current_user
from app.services.inspection import (
    calculate_inspection,
    get_inspection_price,
    validate_inspection_data,
    quick_inspection
)
from app.services.carapi_service import get_carapi_service
from app.services.vin_validator import vin_validator
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inspections", tags=["Inspections"])


# ─── Pydantic Models ──────────────────────────────────────────

class InspectorData(BaseModel):
    """Inspector data model"""
    name: str = Field(..., description="Inspector name")
    credentials: Optional[str] = Field(None, description="Inspector credentials")
    signature: Optional[str] = Field(None, description="Inspector signature")
    license_number: Optional[str] = Field(None, description="Inspector license number")


class VehicleInspectionData(BaseModel):
    """Vehicle inspection data model"""
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: int = Field(..., description="Vehicle year")
    vin: Optional[str] = Field(None, description="Vehicle VIN")
    registration_number: Optional[str] = Field(None, description="Vehicle registration")
    odometer: Optional[int] = Field(0, description="Vehicle odometer reading")
    condition: Optional[str] = Field("Good", description="Vehicle condition")
    accident_history: Optional[str] = Field("None", description="Accident history")
    
    # Ratings
    engine_rating: Optional[str] = Field("Good", description="Engine rating")
    transmission_rating: Optional[str] = Field("Good", description="Transmission rating")
    suspension_rating: Optional[str] = Field("Good", description="Suspension rating")
    brakes_rating: Optional[str] = Field("Good", description="Brakes rating")
    paint_rating: Optional[str] = Field("Good", description="Paint rating")
    chassis_rating: Optional[str] = Field("Good", description="Chassis rating")
    interior_rating: Optional[str] = Field("Good", description="Interior rating")
    electronics_rating: Optional[str] = Field("Good", description="Electronics rating")
    
    tyre_depth_mm: Optional[float] = Field(6.0, description="Tyre depth in mm")
    
    @validator('vin')
    def validate_vin(cls, v):
        if v and len(v) != 17:
            raise ValueError('VIN must be 17 characters')
        return v.upper() if v else v
    
    @validator('year')
    def validate_year(cls, v):
        if v < 1900 or v > datetime.now().year + 1:
            raise ValueError(f'Year must be between 1900 and {datetime.now().year + 1}')
        return v


class CreateInspectionRequest(BaseModel):
    """Create inspection request model"""
    vehicle_data: VehicleInspectionData = Field(..., description="Vehicle data")
    inspection_type: Optional[str] = Field("Premium", description="Inspection type")
    purpose: Optional[str] = Field("Pre-Purchase", description="Inspection purpose")
    region: Optional[str] = Field("Nairobi", description="Region")
    inspector: Optional[InspectorData] = Field(None, description="Inspector data")
    image_urls: Optional[Dict[str, str]] = Field(None, description="Image URLs")
    document_urls: Optional[Dict[str, str]] = Field(None, description="Document URLs")


class QuickEstimateRequest(BaseModel):
    """Quick estimate request model"""
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: int = Field(..., description="Vehicle year")
    odometer: Optional[int] = Field(0, description="Vehicle odometer")
    condition: Optional[str] = Field("good", description="Vehicle condition")


class InspectionResponse(BaseModel):
    """Inspection response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    inspection: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None
    count: Optional[int] = None
    timestamp: Optional[str] = None


# ─── Helper Functions ──────────────────────────────────────────

def generate_certificate_number() -> str:
    """Generate a unique certificate number."""
    return f"INS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()


# ─── Routes ──────────────────────────────────────────────────

@router.post("/", response_model=InspectionResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def create_inspection(
    request: CreateInspectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new vehicle inspection.
    
    **Request Body:**
    - `vehicle_data`: Vehicle details (make, model, year, vin, etc.)
    - `inspection_type`: Type of inspection (Standard, Premium, Express)
    - `purpose`: Purpose of inspection (Pre-Purchase, Insurance, etc.)
    - `region`: Region
    - `inspector`: Inspector details
    - `image_urls`: Image URLs
    - `document_urls`: Document URLs
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Inspection record
    - `inspection`: Inspection results
    - `error`: Error message if unsuccessful
    """
    try:
        vehicle_data = request.vehicle_data.dict()
        
        # If VIN provided, try to auto-fill
        vin = vehicle_data.get('vin')
        if vin:
            vin = vin.upper().strip()
            if vin_validator.is_valid(vin):
                try:
                    carapi = get_carapi_service()
                    vin_data = carapi.decode_vin(vin)
                    if 'error' not in vin_data:
                        vehicle_data['make'] = vin_data.get('make', vehicle_data.get('make'))
                        vehicle_data['model'] = vin_data.get('model', vehicle_data.get('model'))
                        vehicle_data['year'] = vin_data.get('year', vehicle_data.get('year'))
                except Exception as e:
                    logger.warning(f"CarAPI lookup failed: {str(e)}")
        
        # Validate required fields
        required = ['make', 'model', 'year']
        for field in required:
            if not vehicle_data.get(field):
                return InspectionResponse(
                    success=False,
                    error=f"Missing field: {field}"
                )
        
        # Validate data
        is_valid, error = validate_inspection_data(vehicle_data)
        if not is_valid:
            return InspectionResponse(
                success=False,
                error=error
            )
        
        # Get inspector from data or use default
        inspector_data = request.inspector.dict() if request.inspector else {}
        if not inspector_data.get('name'):
            inspector_data = {
                'name': current_user.get('full_name', current_user.get('email', 'Unknown')),
                'credentials': 'AUTO-V-System',
                'signature': current_user.get('email', 'Unknown')
            }
        
        # Get inspection parameters
        inspection_type = request.inspection_type or 'Premium'
        purpose = request.purpose or 'Pre-Purchase'
        region = request.region or 'Nairobi'
        
        # Calculate inspection
        try:
            result = calculate_inspection(
                make=vehicle_data.get('make'),
                model=vehicle_data.get('model'),
                year=int(vehicle_data.get('year', 0)),
                odometer=int(vehicle_data.get('odometer', 0)),
                engine_rating=vehicle_data.get('engine_rating', 'Good'),
                transmission_rating=vehicle_data.get('transmission_rating', 'Good'),
                suspension_rating=vehicle_data.get('suspension_rating', 'Good'),
                brakes_rating=vehicle_data.get('brakes_rating', 'Good'),
                paint_rating=vehicle_data.get('paint_rating', 'Good'),
                chassis_rating=vehicle_data.get('chassis_rating', 'Good'),
                interior_rating=vehicle_data.get('interior_rating', 'Good'),
                electronics_rating=vehicle_data.get('electronics_rating', 'Good'),
                tyre_depth_mm=float(vehicle_data.get('tyre_depth_mm', 6.0)),
                accident_history=vehicle_data.get('accident_history', 'none'),
                inspector_name=inspector_data.get('name'),
                inspector_credentials=inspector_data.get('credentials'),
                inspector_signature=inspector_data.get('signature'),
                inspection_type=inspection_type,
                region=region,
                purpose=purpose,
                inspector=inspector_data
            )
        except ValueError as e:
            return InspectionResponse(
                success=False,
                error=f"Invalid numeric value: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Inspection calculation error: {e}")
            return InspectionResponse(
                success=False,
                error="Inspection calculation failed"
            )
        
        # Generate certificate number
        certificate_number = generate_certificate_number()
        result['certificate_number'] = certificate_number
        result['user_id'] = current_user.get('id')
        
        # Save to Supabase
        request_data = {
            'user_id': current_user.get('id'),
            'service_type': 'inspection',
            'registration_number': vehicle_data.get('registration_number'),
            'vin': vehicle_data.get('vin'),
            'make': vehicle_data.get('make'),
            'model': vehicle_data.get('model'),
            'year': vehicle_data.get('year'),
            'odometer': vehicle_data.get('odometer'),
            'condition': vehicle_data.get('condition', 'Good'),
            'accident_history': vehicle_data.get('accident_history', 'None'),
            'inspection_type': inspection_type,
            'purpose': purpose,
            'amount': get_inspection_price(purpose),
            'payment_status': 'paid',
            'status': 'completed',
            'result': result,
            'inspector': inspector_data,
            'image_urls': request.image_urls or {},
            'document_urls': request.document_urls or {},
            'created_at': format_timestamp(),
            'updated_at': format_timestamp()
        }
        
        # Insert into database
        response = supabase.table('service_requests').insert(request_data).execute()
        
        if not response.data:
            logger.error("Failed to save inspection for user %s", current_user.get('id'))
            return InspectionResponse(
                success=False,
                error="Failed to save inspection"
            )
        
        return InspectionResponse(
            success=True,
            data=response.data[0],
            inspection=result,
            message="Inspection created successfully",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Create inspection error: {str(e)}", exc_info=True)
        return InspectionResponse(
            success=False,
            error=str(e)
        )


@router.get("/{inspection_id}", response_model=InspectionResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_inspection(
    inspection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get inspection by ID.
    
    **Path Parameter:**
    - `inspection_id`: Inspection ID to retrieve
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Inspection data
    - `error`: Error message if unsuccessful
    """
    try:
        # Get inspection from database
        response = supabase.table('service_requests') \
            .select('*') \
            .eq('id', inspection_id) \
            .execute()
        
        if not response.data:
            return InspectionResponse(
                success=False,
                error="Inspection not found"
            )
        
        inspection = response.data[0]
        
        # Check permissions
        if inspection.get('user_id') != current_user.get('id') and current_user.get('role') not in ["admin", "super_admin"]:
            return InspectionResponse(
                success=False,
                error="Access denied"
            )
        
        return InspectionResponse(
            success=True,
            data=inspection,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get inspection error: {str(e)}", exc_info=True)
        return InspectionResponse(
            success=False,
            error=str(e)
        )


@router.get("/user/{user_id}", response_model=InspectionResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_user_inspections(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all inspections for a user.
    
    **Path Parameter:**
    - `user_id`: User ID
    
    **Query Parameters:**
    - `limit`: Number of results to return (default: 50)
    - `offset`: Number of results to skip (default: 0)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of inspections
    - `count`: Total count
    - `error`: Error message if unsuccessful
    """
    try:
        # Check permissions
        if user_id != current_user.get('id') and current_user.get('role') not in ["admin", "super_admin"]:
            return InspectionResponse(
                success=False,
                error="Access denied"
            )
        
        # Get inspections from database
        response = supabase.table('service_requests') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('service_type', 'inspection') \
            .order('created_at', desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        
        return InspectionResponse(
            success=True,
            data=response.data,
            count=len(response.data),
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get user inspections error: {str(e)}", exc_info=True)
        return InspectionResponse(
            success=False,
            error=str(e)
        )


@router.post("/quick-estimate", response_model=InspectionResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def quick_estimate(
    request: QuickEstimateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Quick inspection estimate.
    
    **Request Body:**
    - `make`: Vehicle make
    - `model`: Vehicle model
    - `year`: Vehicle year
    - `odometer`: Vehicle odometer (optional)
    - `condition`: Vehicle condition (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Quick estimate results
    - `error`: Error message if unsuccessful
    """
    try:
        # Validate required fields
        if not request.make or not request.model or not request.year:
            return InspectionResponse(
                success=False,
                error="Make, model, and year are required"
            )
        
        # Calculate quick estimate
        result = quick_inspection(
            make=request.make,
            model=request.model,
            year=request.year,
            odometer=request.odometer or 0,
            condition=request.condition or 'good'
        )
        
        return InspectionResponse(
            success=True,
            data={
                'overall_score': result.get('overall_score', 0),
                'safety_score': result.get('safety_score', 0),
                'mechanical_score': result.get('mechanical_score', 0),
                'confidence_score': result.get('confidence_score', 0),
                'issues': result.get('issues', [])[:3]
            },
            message="Quick estimate completed",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Quick estimate error: {str(e)}", exc_info=True)
        return InspectionResponse(
            success=False,
            error=str(e)
        )


@router.get("/stats", response_model=InspectionResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_inspection_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get inspection statistics.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Statistics (total, completed, pending, avg_score)
    - `error`: Error message if unsuccessful
    """
    try:
        # Get inspections from database
        response = supabase.table('service_requests') \
            .select('*') \
            .eq('user_id', current_user.get('id')) \
            .eq('service_type', 'inspection') \
            .execute()
        
        total = len(response.data)
        completed = len([r for r in response.data if r.get('status') == 'completed'])
        pending = total - completed
        
        # Calculate average score from results
        total_score = 0
        score_count = 0
        for r in response.data:
            result = r.get('result', {})
            if result.get('overall_score'):
                total_score += result.get('overall_score', 0)
                score_count += 1
        
        avg_score = total_score / score_count if score_count > 0 else 0
        
        return InspectionResponse(
            success=True,
            data={
                'total': total,
                'completed': completed,
                'pending': pending,
                'avg_score': avg_score
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Inspection stats error: {str(e)}", exc_info=True)
        return InspectionResponse(
            success=False,
            error=str(e)
        )


@router.get("/prices", response_model=InspectionResponse)
@rate_limit(limit=20, per=60)
@log_request
@handle_errors
async def get_inspection_prices():
    """
    Get inspection prices.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Price list by purpose
    """
    try:
        prices = {
            "Pre-Purchase": get_inspection_price("Pre-Purchase"),
            "Insurance": get_inspection_price("Insurance"),
            "Lease": get_inspection_price("Lease"),
            "Certification": get_inspection_price("Certification"),
            "Auction": get_inspection_price("Auction"),
            "Export": get_inspection_price("Export")
        }
        
        return InspectionResponse(
            success=True,
            data=prices,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Inspection prices error: {str(e)}", exc_info=True)
        return InspectionResponse(
            success=False,
            error=str(e)
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
