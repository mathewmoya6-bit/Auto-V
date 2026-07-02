"""
Instant Value Routes - FastAPI Version
Instant vehicle valuation, quick estimates, and real-time market data
Uses SQLAlchemy ORM with FastAPI - No Supabase dependency
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_optional
from app.services.carapi_service import get_carapi_service
from app.services.valuation_service import get_valuation_service
from app.services.vin_validator import vin_validator
from app.models import ServiceRequest, Vehicle, User, Certificate
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/instant-value", tags=["Instant Value"])


# ─── Pydantic Models ──────────────────────────────────────────

class InstantValueRequest(BaseModel):
    """Instant value request model"""
    vin: Optional[str] = Field(None, description="Vehicle VIN", min_length=17, max_length=17)
    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")
    year: Optional[int] = Field(None, description="Vehicle year", ge=1900, le=datetime.now().year + 1)
    registration_number: Optional[str] = Field(None, description="Vehicle registration number")
    odometer: Optional[int] = Field(0, description="Vehicle odometer in km", ge=0)
    condition: Optional[str] = Field("Good", description="Vehicle condition")
    region: Optional[str] = Field("Nairobi", description="Region")
    
    @validator('vin')
    def validate_vin(cls, v):
        if v:
            v = v.upper().strip()
            if len(v) != 17:
                raise ValueError('VIN must be 17 characters')
            invalid_chars = ['I', 'O', 'Q']
            for char in invalid_chars:
                if char in v:
                    raise ValueError(f'VIN contains invalid character: {char}')
            return v
        return v


class InstantValueResponse(BaseModel):
    """Instant value response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    source: Optional[str] = None
    timestamp: Optional[str] = None


class InstantValueHistoryRequest(BaseModel):
    """Instant value history request model"""
    limit: Optional[int] = Field(10, ge=1, le=50, description="Number of results")
    offset: Optional[int] = Field(0, ge=0, description="Offset for pagination")


class BulkInstantValueRequest(BaseModel):
    """Bulk instant value request model"""
    vehicles: List[Dict[str, Any]] = Field(..., description="List of vehicles to value")
    
    @validator('vehicles')
    def validate_vehicles(cls, v):
        if len(v) > 20:
            raise ValueError('Maximum 20 vehicles per request')
        return v


# ─── Helper Functions ──────────────────────────────────────────

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()


def calculate_instant_value(
    make: str,
    model: str,
    year: int,
    odometer: int = 0,
    condition: str = 'Good',
    region: str = 'Nairobi'
) -> Dict[str, Any]:
    """
    Calculate instant vehicle value.
    """
    # Base values by make
    base_values = {
        'Toyota': 2800000,
        'Honda': 2500000,
        'BMW': 4500000,
        'Mercedes-Benz': 5000000,
        'Audi': 4200000,
        'Nissan': 2300000,
        'Ford': 2100000,
        'Volkswagen': 2400000,
        'Subaru': 2600000,
        'Mazda': 2200000,
        'Kia': 2100000,
        'Hyundai': 2200000,
        'Lexus': 4000000,
        'Land Rover': 5500000,
        'Jeep': 3500000,
        'Other': 2500000
    }
    
    # Region multipliers
    region_multipliers = {
        'Nairobi': 1.0,
        'Mombasa': 0.92,
        'Kisumu': 0.88,
        'Nakuru': 0.90,
        'Eldoret': 0.89,
        'National': 0.95
    }
    
    base = base_values.get(make, 2500000)
    current_year = datetime.now().year
    year_factor = 1 - ((current_year - year) * 0.08)
    year_factor = max(0.3, year_factor)
    
    mileage_factor = max(0.4, 1 - (odometer / 300000))
    
    condition_factors = {
        'Excellent': 1.2,
        'Good': 1.0,
        'Fair': 0.85,
        'Poor': 0.6
    }
    condition_factor = condition_factors.get(condition, 1.0)
    
    region_factor = region_multipliers.get(region, 1.0)
    
    market_value = int(base * year_factor * mileage_factor * condition_factor * region_factor)
    market_value = max(150000, min(market_value, base * 1.2))
    
    return {
        'market_value': market_value,
        'insurance_value': int(market_value * 1.15),
        'trade_in_value': int(market_value * 0.8),
        'forced_sale_value': int(market_value * 0.65),
        'condition_score': 7.5,
        'confidence_score': 85,
        'risk_score': 15,
        'valuation_date': datetime.now().isoformat(),
        'factors_used': {
            'base_value': base,
            'year_factor': round(year_factor, 3),
            'mileage_factor': round(mileage_factor, 3),
            'condition_factor': condition_factor,
            'region_factor': region_factor
        }
    }


def generate_reference_number() -> str:
    """Generate a unique reference number for instant value."""
    return f"IV-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"


# ─── Routes ──────────────────────────────────────────────────

@router.post("/check", response_model=InstantValueResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def instant_value_check(
    request: InstantValueRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get instant vehicle value.
    
    **Request Body:**
    - `vin`: Vehicle VIN (optional)
    - `make`: Vehicle make (optional)
    - `model`: Vehicle model (optional)
    - `year`: Vehicle year (optional)
    - `registration_number`: Vehicle registration (optional)
    - `odometer`: Vehicle odometer (optional)
    - `condition`: Vehicle condition (optional)
    - `region`: Region (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Instant valuation results
    - `source`: Data source
    - `error`: Error message if unsuccessful
    """
    try:
        vin = request.vin.upper().strip() if request.vin else None
        registration = request.registration_number.upper().strip() if request.registration_number else None
        
        # Try to get vehicle from database
        vehicle_data = None
        existing_vehicle = None
        
        if vin:
            existing_vehicle = db.query(Vehicle).filter(Vehicle.vin == vin).first()
        elif registration:
            existing_vehicle = db.query(Vehicle).filter(
                Vehicle.registration_number == registration
            ).first()
        
        # Use existing vehicle data or request data
        if existing_vehicle:
            vehicle_data = {
                'make': existing_vehicle.make,
                'model': existing_vehicle.model,
                'year': existing_vehicle.year,
                'odometer': existing_vehicle.odometer,
                'vin': existing_vehicle.vin,
                'registration_number': existing_vehicle.registration_number
            }
        else:
            # Try CarAPI for VIN decode
            if vin:
                carapi = get_carapi_service()
                vin_result = carapi.decode_vin(vin)
                if "error" not in vin_result:
                    vehicle_data = {
                        'make': vin_result.get('make', request.make),
                        'model': vin_result.get('model', request.model),
                        'year': vin_result.get('year', request.year),
                        'odometer': request.odometer or 0,
                        'vin': vin,
                        'registration_number': registration
                    }
            
            # Fallback to request data
            if not vehicle_data:
                if not request.make and not request.model and not request.year:
                    return InstantValueResponse(
                        success=False,
                        error="Insufficient vehicle information. Please provide make, model, and year."
                    )
                vehicle_data = {
                    'make': request.make or 'Unknown',
                    'model': request.model or 'Unknown',
                    'year': request.year or 2020,
                    'odometer': request.odometer or 0,
                    'vin': vin,
                    'registration_number': registration
                }
        
        # Calculate instant value
        valuation = calculate_instant_value(
            make=vehicle_data['make'],
            model=vehicle_data['model'],
            year=vehicle_data['year'],
            odometer=vehicle_data['odometer'],
            condition=request.condition or 'Good',
            region=request.region or 'Nairobi'
        )
        
        # Save to history
        reference_number = generate_reference_number()
        result_data = {
            'reference_number': reference_number,
            'vehicle': vehicle_data,
            'valuation': valuation,
            'request_details': {
                'condition': request.condition or 'Good',
                'region': request.region or 'Nairobi',
                'timestamp': format_timestamp()
            }
        }
        
        # Save to database
        service_request = ServiceRequest(
            user_id=current_user.get('id'),
            service_type='instant_value',
            amount=500,  # Default fee for instant check
            vehicle_reg=vehicle_data.get('registration_number'),
            vehicle_make=vehicle_data.get('make'),
            vehicle_model=vehicle_data.get('model'),
            vehicle_year=vehicle_data.get('year'),
            vehicle_mileage=vehicle_data.get('odometer'),
            vehicle_condition=request.condition or 'Good',
            result=result_data,
            payment_status='paid',
            status='completed',
            completed_at=datetime.utcnow()
        )
        db.add(service_request)
        db.commit()
        db.refresh(service_request)
        
        return InstantValueResponse(
            success=True,
            data={
                "reference_number": reference_number,
                "vehicle": vehicle_data,
                "valuation": valuation,
                "source": "Database" if existing_vehicle else "CarAPI + Internal",
                "request_id": service_request.id
            },
            source="AUTO-V Instant Value Engine",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Instant value error: {str(e)}", exc_info=True)
        db.rollback()
        return InstantValueResponse(
            success=False,
            error=str(e)
        )


@router.get("/history", response_model=InstantValueResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_instant_value_history(
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get instant value history for the current user.
    
    **Query Parameters:**
    - `limit`: Number of results (default: 10, max: 50)
    - `offset`: Offset for pagination (default: 0)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of instant value checks
    - `count`: Total count
    - `error`: Error message if unsuccessful
    """
    try:
        # Query instant value history
        query = db.query(ServiceRequest).filter(
            ServiceRequest.user_id == current_user.get('id'),
            ServiceRequest.service_type == 'instant_value'
        )
        
        total = query.count()
        history = query.order_by(desc(ServiceRequest.created_at)).offset(offset).limit(limit).all()
        
        return InstantValueResponse(
            success=True,
            data={
                "history": [
                    {
                        "id": str(r.id),
                        "reference_number": r.result.get('reference_number') if r.result else None,
                        "vehicle": {
                            "make": r.vehicle_make,
                            "model": r.vehicle_model,
                            "year": r.vehicle_year,
                            "registration": r.vehicle_reg,
                            "mileage": r.vehicle_mileage
                        },
                        "valuation": r.result.get('valuation') if r.result else None,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "status": r.status
                    }
                    for r in history
                ],
                "total": total,
                "limit": limit,
                "offset": offset
            },
            source="Database",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get instant value history error: {str(e)}", exc_info=True)
        return InstantValueResponse(
            success=False,
            error=str(e)
        )


@router.get("/{reference_number}", response_model=InstantValueResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_instant_value_by_reference(
    reference_number: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get instant value by reference number.
    
    **Path Parameter:**
    - `reference_number`: Reference number of the instant value check
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Instant value data
    - `error`: Error message if unsuccessful
    """
    try:
        # Query by reference number
        service_request = db.query(ServiceRequest).filter(
            ServiceRequest.user_id == current_user.get('id'),
            ServiceRequest.service_type == 'instant_value',
            ServiceRequest.result.has_key('reference_number'),
            ServiceRequest.result['reference_number'].astext == reference_number
        ).first()
        
        if not service_request:
            return InstantValueResponse(
                success=False,
                error="Instant value record not found"
            )
        
        return InstantValueResponse(
            success=True,
            data={
                "id": str(service_request.id),
                "reference_number": reference_number,
                "vehicle": {
                    "make": service_request.vehicle_make,
                    "model": service_request.vehicle_model,
                    "year": service_request.vehicle_year,
                    "registration": service_request.vehicle_reg,
                    "mileage": service_request.vehicle_mileage
                },
                "valuation": service_request.result.get('valuation') if service_request.result else None,
                "created_at": service_request.created_at.isoformat() if service_request.created_at else None,
                "status": service_request.status
            },
            source="Database",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get instant value by reference error: {str(e)}", exc_info=True)
        return InstantValueResponse(
            success=False,
            error=str(e)
        )


@router.post("/bulk", response_model=InstantValueResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def bulk_instant_value(
    request: BulkInstantValueRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get instant values for multiple vehicles.
    
    **Request Body:**
    - `vehicles`: List of vehicles with make, model, year, odometer, condition
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of instant valuations
    - `error`: Error message if unsuccessful
    """
    try:
        results = []
        total_value = 0
        
        for vehicle in request.vehicles:
            make = vehicle.get('make', 'Unknown')
            model = vehicle.get('model', 'Unknown')
            year = vehicle.get('year', 2020)
            odometer = vehicle.get('odometer', 0)
            condition = vehicle.get('condition', 'Good')
            region = vehicle.get('region', 'Nairobi')
            
            valuation = calculate_instant_value(
                make=make,
                model=model,
                year=year,
                odometer=odometer,
                condition=condition,
                region=region
            )
            
            results.append({
                "vehicle": {
                    "make": make,
                    "model": model,
                    "year": year,
                    "odometer": odometer,
                    "condition": condition,
                    "region": region
                },
                "valuation": valuation
            })
            total_value += valuation.get('market_value', 0)
        
        # Save bulk request to database
        result_data = {
            'total_vehicles': len(results),
            'total_value': total_value,
            'average_value': total_value / len(results) if results else 0,
            'results': results
        }
        
        service_request = ServiceRequest(
            user_id=current_user.get('id'),
            service_type='instant_value_bulk',
            amount=len(results) * 500,  # 500 per vehicle
            result=result_data,
            payment_status='paid',
            status='completed',
            completed_at=datetime.utcnow()
        )
        db.add(service_request)
        db.commit()
        db.refresh(service_request)
        
        return InstantValueResponse(
            success=True,
            data={
                "request_id": str(service_request.id),
                "total_vehicles": len(results),
                "total_value": total_value,
                "average_value": total_value / len(results) if results else 0,
                "results": results
            },
            source="AUTO-V Instant Value Engine",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Bulk instant value error: {str(e)}", exc_info=True)
        db.rollback()
        return InstantValueResponse(
            success=False,
            error=str(e)
        )


@router.get("/stats", response_model=InstantValueResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_instant_value_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get instant value statistics.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Statistics
    - `error`: Error message if unsuccessful
    """
    try:
        # Get stats for the current user
        user_checks = db.query(ServiceRequest).filter(
            ServiceRequest.user_id == current_user.get('id'),
            ServiceRequest.service_type == 'instant_value'
        )
        
        total_checks = user_checks.count()
        completed = user_checks.filter(ServiceRequest.status == 'completed').count()
        
        # Get average value
        avg_result = db.query(
            func.avg(
                func.cast(
                    func.json_extract_path_text(
                        ServiceRequest.result, 'valuation', 'market_value'
                    ), 
                    func.numeric()
                )
            )
        ).filter(
            ServiceRequest.user_id == current_user.get('id'),
            ServiceRequest.service_type == 'instant_value',
            ServiceRequest.result.isnot(None)
        ).scalar()
        
        # Get recent activity
        recent = user_checks.order_by(desc(ServiceRequest.created_at)).limit(5).all()
        
        return InstantValueResponse(
            success=True,
            data={
                "total_checks": total_checks,
                "completed": completed,
                "average_value": float(avg_result) if avg_result else 0,
                "recent": [
                    {
                        "id": str(r.id),
                        "reference_number": r.result.get('reference_number') if r.result else None,
                        "vehicle": f"{r.vehicle_make} {r.vehicle_model} ({r.vehicle_year})",
                        "value": r.result.get('valuation', {}).get('market_value') if r.result else None,
                        "created_at": r.created_at.isoformat() if r.created_at else None
                    }
                    for r in recent
                ]
            },
            source="Database",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get instant value stats error: {str(e)}", exc_info=True)
        return InstantValueResponse(
            success=False,
            error=str(e)
        )


@router.post("/compare", response_model=InstantValueResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def compare_instant_values(
    request: InstantValueRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compare instant value with market average.
    
    **Request Body:**
    - `vin`: Vehicle VIN (optional)
    - `make`: Vehicle make (optional)
    - `model`: Vehicle model (optional)
    - `year`: Vehicle year (optional)
    - `odometer`: Vehicle odometer (optional)
    - `condition`: Vehicle condition (optional)
    - `region`: Region (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Comparison results
    - `error`: Error message if unsuccessful
    """
    try:
        # Get instant value
        make = request.make or 'Toyota'
        model = request.model or 'RAV4'
        year = request.year or 2020
        odometer = request.odometer or 0
        condition = request.condition or 'Good'
        region = request.region or 'Nairobi'
        
        valuation = calculate_instant_value(
            make=make,
            model=model,
            year=year,
            odometer=odometer,
            condition=condition,
            region=region
        )
        
        # Get market average from database
        market_avg = db.query(
            func.avg(
                func.json_extract_path_text(
                    ServiceRequest.result, 'valuation', 'market_value'
                )
            )
        ).filter(
            ServiceRequest.service_type == 'valuation',
            ServiceRequest.vehicle_make == make,
            ServiceRequest.vehicle_model == model,
            ServiceRequest.status == 'completed'
        ).scalar()
        
        market_avg = float(market_avg) if market_avg else valuation.get('market_value', 0) * 0.95
        
        current_value = valuation.get('market_value', 0)
        difference = current_value - market_avg
        difference_percentage = round((difference / market_avg) * 100, 2) if market_avg > 0 else 0
        
        return InstantValueResponse(
            success=True,
            data={
                "current_valuation": valuation,
                "market_average": market_avg,
                "comparison": {
                    "difference": difference,
                    "difference_percentage": difference_percentage,
                    "is_above_average": difference > 0,
                    "status": "Above average" if difference > 0 else "Below average" if difference < 0 else "At market average"
                },
                "vehicle": {
                    "make": make,
                    "model": model,
                    "year": year,
                    "odometer": odometer,
                    "condition": condition,
                    "region": region
                }
            },
            source="AUTO-V Comparison Engine",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Compare instant value error: {str(e)}", exc_info=True)
        return InstantValueResponse(
            success=False,
            error=str(e)
        )


@router.get("/prices", response_model=InstantValueResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_instant_value_prices(
    current_user: dict = Depends(get_current_user)
):
    """
    Get instant value pricing.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Pricing information
    - `error`: Error message if unsuccessful
    """
    try:
        return InstantValueResponse(
            success=True,
            data={
                "instant_value": 500,
                "bulk_instant_value": 500,  # per vehicle
                "history": 0,  # free
                "comparison": 300
            },
            source="AUTO-V Pricing Engine",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get instant value prices error: {str(e)}", exc_info=True)
        return InstantValueResponse(
            success=False,
            error=str(e)
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
