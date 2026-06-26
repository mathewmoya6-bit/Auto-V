"""
Valuation Routes - FastAPI Version
Vehicle valuation creation, retrieval, quick estimates, and statistics
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging

from app.core.database import supabase
from app.core.dependencies import get_current_user, get_current_user_optional
from app.services.valuation import calculate_value, get_valuation_price, validate_valuation_data
from app.services.carapi_service import get_carapi_service
from app.services.vin_validator import vin_validator
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/valuations", tags=["Valuations"])


# ─── Pydantic Models ──────────────────────────────────────────

class ValuationVehicleData(BaseModel):
    """Valuation vehicle data model"""
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: int = Field(..., description="Vehicle year")
    vin: Optional[str] = Field(None, description="Vehicle VIN")
    registration_number: Optional[str] = Field(None, description="Vehicle registration")
    odometer: Optional[int] = Field(0, description="Vehicle odometer")
    condition: Optional[str] = Field("Good", description="Vehicle condition")
    accident_history: Optional[str] = Field("None", description="Accident history")
    service_history: Optional[str] = Field("Full", description="Service history")
    owners: Optional[int] = Field(1, description="Number of owners")
    usage: Optional[str] = Field("Personal", description="Usage type")
    import_status: Optional[str] = Field("Local", description="Import status")
    warranty: Optional[str] = Field("Expired", description="Warranty status")
    modifications: Optional[str] = Field("None", description="Modifications")
    region: Optional[str] = Field("Nairobi", description="Region")
    engine_cc: Optional[int] = Field(None, description="Engine capacity")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    color: Optional[str] = Field(None, description="Vehicle color")
    
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


class ValuationRequest(BaseModel):
    """Valuation request model"""
    vehicle_data: ValuationVehicleData = Field(..., description="Vehicle data")
    purpose: Optional[str] = Field("market_value", description="Valuation purpose")
    methodology: Optional[str] = Field("market_comparison", description="Valuation methodology")
    inspector: Optional[Dict[str, Any]] = Field(None, description="Inspector data")
    notes: Optional[str] = Field(None, description="Additional notes")


class ValuationUpdate(BaseModel):
    """Valuation update model"""
    status: Optional[str] = None
    notes: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class ValuationResponse(BaseModel):
    """Valuation response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    valuation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    count: Optional[int] = None
    timestamp: Optional[str] = None


class QuickEstimateRequest(BaseModel):
    """Quick estimate request model"""
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: int = Field(..., description="Vehicle year")
    odometer: Optional[int] = Field(0, description="Vehicle odometer")
    condition: Optional[str] = Field("good", description="Vehicle condition")
    region: Optional[str] = Field("nairobi", description="Region")


# ─── Helper Functions ──────────────────────────────────────────

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()


def generate_certificate_number() -> str:
    """Generate a unique certificate number."""
    return f"VAL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def get_default_inspector(user: dict) -> Dict[str, Any]:
    """Get default inspector data from user."""
    return {
        "name": user.get("full_name", user.get("email", "Unknown")),
        "credentials": "AUTO-V-System",
        "signature": user.get("email", "Unknown"),
        "license_number": user.get("license_number", "N/A")
    }


# ─── Routes ──────────────────────────────────────────────────

@router.post("/", response_model=ValuationResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def create_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new vehicle valuation.
    
    **Request Body:**
    - `vehicle_data`: Vehicle details (make, model, year, vin, etc.)
    - `purpose`: Valuation purpose (market_value, insurance, forced_sale, etc.)
    - `methodology`: Valuation methodology
    - `inspector`: Inspector details
    - `notes`: Additional notes
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Valuation record
    - `valuation`: Valuation results
    - `error`: Error message if unsuccessful
    """
    try:
        vehicle_data = request.vehicle_data.dict()
        purpose = request.purpose or "market_value"
        
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
                        vehicle_data['engine_cc'] = vin_data.get('engine_cc', vehicle_data.get('engine_cc'))
                        vehicle_data['fuel_type'] = vin_data.get('fuel_type', vehicle_data.get('fuel_type'))
                        vehicle_data['transmission'] = vin_data.get('transmission', vehicle_data.get('transmission'))
                except Exception as e:
                    logger.warning(f"CarAPI lookup failed: {str(e)}")
        
        # Validate required fields
        required = ['make', 'model', 'year']
        for field in required:
            if not vehicle_data.get(field):
                return ValuationResponse(
                    success=False,
                    error=f"Missing field: {field}"
                )
        
        # Validate data
        is_valid, error = validate_valuation_data(vehicle_data)
        if not is_valid:
            return ValuationResponse(
                success=False,
                error=error
            )
        
        # Get inspector from data or use default
        inspector = request.inspector or get_default_inspector(current_user)
        if not inspector.get('name'):
            inspector = get_default_inspector(current_user)
        
        # Call valuation engine
        try:
            result = calculate_value(
                make=vehicle_data.get('make'),
                model=vehicle_data.get('model'),
                year=int(vehicle_data.get('year', 0)),
                odometer=int(vehicle_data.get('odometer', 0)),
                condition=vehicle_data.get('condition', 'Good'),
                accident_history=vehicle_data.get('accident_history', 'None'),
                service_history=vehicle_data.get('service_history', 'Full'),
                owners=int(vehicle_data.get('owners', 1)),
                usage=vehicle_data.get('usage', 'Personal'),
                import_status=vehicle_data.get('import_status', 'Local'),
                warranty=vehicle_data.get('warranty', 'Expired'),
                modifications=vehicle_data.get('modifications', 'None'),
                region=vehicle_data.get('region', 'Nairobi'),
                purpose=purpose,
                valuation_methodology=request.methodology or 'market_comparison',
                inspector=inspector,
                current_year=datetime.now().year
            )
        except ValueError as e:
            return ValuationResponse(
                success=False,
                error=f"Invalid numeric value: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Valuation calculation error: {e}")
            return ValuationResponse(
                success=False,
                error="Valuation calculation failed"
            )
        
        # Generate certificate number
        certificate_number = generate_certificate_number()
        result['certificate_number'] = certificate_number
        result['user_id'] = current_user.get('id')
        
        # Prepare request data
        request_data = {
            'user_id': current_user.get('id'),
            'service_type': 'valuation',
            'registration_number': vehicle_data.get('registration_number'),
            'vin': vehicle_data.get('vin'),
            'make': vehicle_data.get('make'),
            'model': vehicle_data.get('model'),
            'year': vehicle_data.get('year'),
            'odometer': vehicle_data.get('odometer'),
            'condition': vehicle_data.get('condition', 'Good'),
            'accident_history': vehicle_data.get('accident_history', 'None'),
            'valuation_purpose': purpose,
            'valuation_methodology': request.methodology or 'market_comparison',
            'amount': get_valuation_price(purpose),
            'payment_status': 'paid',
            'status': 'completed',
            'result': result,
            'inspector': inspector,
            'notes': request.notes,
            'created_at': format_timestamp(),
            'updated_at': format_timestamp(),
            'completed_at': format_timestamp()
        }
        
        # Save to Supabase
        response = supabase.table('service_requests').insert(request_data).execute()
        
        if not response.data:
            logger.error(f"Failed to save valuation for user {current_user.get('id')}")
            return ValuationResponse(
                success=False,
                error="Failed to save valuation"
            )
        
        return ValuationResponse(
            success=True,
            data=response.data[0],
            valuation=result,
            message="Valuation created successfully",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Create valuation error: {str(e)}", exc_info=True)
        return ValuationResponse(
            success=False,
            error=str(e)
        )


@router.get("/{valuation_id}", response_model=ValuationResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_valuation(
    valuation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get valuation by ID.
    
    **Path Parameter:**
    - `valuation_id`: Valuation ID
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Valuation data
    - `error`: Error message if unsuccessful
    """
    try:
        # Get valuation from database
        response = supabase.table('service_requests') \
            .select('*') \
            .eq('id', valuation_id) \
            .execute()
        
        if not response.data:
            return ValuationResponse(
                success=False,
                error="Valuation not found"
            )
        
        valuation = response.data[0]
        
        # Check permissions
        if valuation.get('user_id') != current_user.get('id') and current_user.get('role') not in ["admin", "super_admin"]:
            return ValuationResponse(
                success=False,
                error="Access denied"
            )
        
        return ValuationResponse(
            success=True,
            data=valuation,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get valuation error: {str(e)}", exc_info=True)
        return ValuationResponse(
            success=False,
            error=str(e)
        )


@router.get("/user/{user_id}", response_model=ValuationResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_user_valuations(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all valuations for a user.
    
    **Path Parameter:**
    - `user_id`: User ID
    
    **Query Parameters:**
    - `limit`: Number of results to return (default: 50)
    - `offset`: Number of results to skip (default: 0)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of valuations
    - `count`: Total count
    - `error`: Error message if unsuccessful
    """
    try:
        # Check permissions
        if user_id != current_user.get('id') and current_user.get('role') not in ["admin", "super_admin"]:
            return ValuationResponse(
                success=False,
                error="Access denied"
            )
        
        # Get valuations from database
        response = supabase.table('service_requests') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('service_type', 'valuation') \
            .order('created_at', desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        
        return ValuationResponse(
            success=True,
            data=response.data,
            count=len(response.data),
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get user valuations error: {str(e)}", exc_info=True)
        return ValuationResponse(
            success=False,
            error=str(e)
        )


@router.get("/vehicle/{vin}", response_model=ValuationResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_valuations_by_vin(
    vin: str,
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """
    Get valuations for a vehicle by VIN.
    
    **Path Parameter:**
    - `vin`: Vehicle VIN
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of valuations
    - `count`: Total count
    - `error`: Error message if unsuccessful
    """
    try:
        vin = vin.upper().strip()
        
        # Get valuations from database
        response = supabase.table('service_requests') \
            .select('*') \
            .eq('vin', vin) \
            .eq('service_type', 'valuation') \
            .order('created_at', desc=True) \
            .limit(limit) \
            .execute()
        
        return ValuationResponse(
            success=True,
            data=response.data,
            count=len(response.data),
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get valuations by VIN error: {str(e)}", exc_info=True)
        return ValuationResponse(
            success=False,
            error=str(e)
        )


@router.post("/quick-estimate", response_model=ValuationResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def quick_estimate(
    request: QuickEstimateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Quick valuation estimate (for instant check).
    
    **Request Body:**
    - `make`: Vehicle make
    - `model`: Vehicle model
    - `year`: Vehicle year
    - `odometer`: Vehicle odometer (optional)
    - `condition`: Vehicle condition (optional)
    - `region`: Region (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Quick estimate results
    - `error`: Error message if unsuccessful
    """
    try:
        # Validate required fields
        if not request.make or not request.model or not request.year:
            return ValuationResponse(
                success=False,
                error="Make, model, and year are required"
            )
        
        # Calculate quick estimate
        result = calculate_value(
            make=request.make,
            model=request.model,
            year=request.year,
            odometer=request.odometer or 0,
            condition=request.condition or 'Good',
            accident_history='None',
            service_history='Full',
            owners=1,
            usage='Personal',
            import_status='Local',
            warranty='Expired',
            modifications='None',
            region=request.region or 'Nairobi',
            purpose='market_value',
            valuation_methodology='quick_estimate',
            inspector={"name": "AUTO-V-System", "credentials": "Quick Estimate"},
            current_year=datetime.now().year
        )
        
        return ValuationResponse(
            success=True,
            data={
                "market_value": result.get("market_value", 0),
                "insurance_value": result.get("insurance_value", 0),
                "forced_sale_value": result.get("forced_sale_value", 0),
                "confidence_score": result.get("confidence_score", 0)
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Quick estimate error: {str(e)}", exc_info=True)
        return ValuationResponse(
            success=False,
            error=str(e)
        )


@router.get("/stats", response_model=ValuationResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_valuation_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get valuation statistics.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Statistics (total, completed, pending, etc.)
    - `error`: Error message if unsuccessful
    """
    try:
        # Get valuations from database
        response = supabase.table('service_requests') \
            .select('*') \
            .eq('user_id', current_user.get('id')) \
            .eq('service_type', 'valuation') \
            .execute()
        
        total = len(response.data)
        completed = len([r for r in response.data if r.get('status') == 'completed'])
        pending = total - completed
        
        # Calculate average values
        total_value = 0
        value_count = 0
        for r in response.data:
            result = r.get('result', {})
            if result.get('market_value'):
                total_value += result.get('market_value', 0)
                value_count += 1
        
        avg_value = total_value / value_count if value_count > 0 else 0
        
        return ValuationResponse(
            success=True,
            data={
                "total": total,
                "completed": completed,
                "pending": pending,
                "avg_value": avg_value,
                "total_value": total_value
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Valuation stats error: {str(e)}", exc_info=True)
        return ValuationResponse(
            success=False,
            error=str(e)
        )


@router.get("/prices", response_model=ValuationResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_valuation_prices(
    current_user: dict = Depends(get_current_user)
):
    """
    Get valuation prices by purpose.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Price list by purpose
    """
    try:
        prices = {
            "market_value": get_valuation_price("market_value"),
            "insurance": get_valuation_price("insurance"),
            "forced_sale": get_valuation_price("forced_sale"),
            "trade_in": get_valuation_price("trade_in"),
            "private_sale": get_valuation_price("private_sale"),
            "finance": get_valuation_price("finance"),
            "lease": get_valuation_price("lease"),
            "export": get_valuation_price("export")
        }
        
        return ValuationResponse(
            success=True,
            data=prices,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get valuation prices error: {str(e)}", exc_info=True)
        return ValuationResponse(
            success=False,
            error=str(e)
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
