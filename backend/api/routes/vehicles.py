"""
Vehicle Routes - FastAPI Version
VIN decoding, valuation, search, photos, stolen check, recalls, plate to VIN, auto-fill
Uses SQLAlchemy ORM with FastAPI - No Supabase dependency
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_optional
from app.services.carapi_service import get_carapi_service
from app.services.vin_validator import vin_validator
from app.services.valuation_service import get_valuation_service
from app.models import Vehicle, User, ServiceRequest, VehicleImage
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vehicles", tags=["Vehicles"])


# ─── Pydantic Models ──────────────────────────────────────────

class VinDecodeRequest(BaseModel):
    """VIN decode request model"""
    vin: str = Field(..., description="Vehicle VIN", min_length=17, max_length=17)
    
    @validator('vin')
    def validate_vin(cls, v):
        v = v.upper().strip()
        if len(v) != 17:
            raise ValueError('VIN must be 17 characters')
        invalid_chars = ['I', 'O', 'Q']
        for char in invalid_chars:
            if char in v:
                raise ValueError(f'VIN contains invalid character: {char}')
        return v


class ValuationRequest(BaseModel):
    """Valuation request model"""
    vin: str = Field(..., description="Vehicle VIN", min_length=17, max_length=17)
    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")
    year: Optional[int] = Field(None, description="Vehicle year", ge=1900, le=datetime.now().year + 1)
    odometer: Optional[int] = Field(0, description="Vehicle odometer in km", ge=0)
    condition: Optional[str] = Field("Good", description="Vehicle condition")
    purpose: Optional[str] = Field("Market Value", description="Valuation purpose")
    region: Optional[str] = Field("Nairobi", description="Region")
    
    @validator('vin')
    def validate_vin(cls, v):
        v = v.upper().strip()
        if len(v) != 17:
            raise ValueError('VIN must be 17 characters')
        return v


class SearchVehiclesRequest(BaseModel):
    """Search vehicles request model"""
    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")
    year: Optional[int] = Field(None, description="Vehicle year", ge=1900, le=datetime.now().year + 1)
    limit: Optional[int] = Field(10, ge=1, le=50, description="Number of results")


class VehiclePhotosRequest(BaseModel):
    """Vehicle photos request model"""
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: Optional[int] = Field(None, description="Vehicle year", ge=1900, le=datetime.now().year + 1)


class RecallsRequest(BaseModel):
    """Recalls request model"""
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: Optional[int] = Field(None, description="Vehicle year", ge=1900, le=datetime.now().year + 1)


class PlateToVinRequest(BaseModel):
    """Plate to VIN request model"""
    plate: str = Field(..., description="License plate number")
    country: Optional[str] = Field("us", description="Country code")


class AutoFillRequest(BaseModel):
    """Auto-fill request model"""
    vin: str = Field(..., description="Vehicle VIN", min_length=17, max_length=17)
    
    @validator('vin')
    def validate_vin(cls, v):
        v = v.upper().strip()
        if len(v) != 17:
            raise ValueError('VIN must be 17 characters')
        return v


class VehicleResponse(BaseModel):
    """Vehicle response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    count: Optional[int] = None
    source: Optional[str] = None
    timestamp: Optional[str] = None


# ─── Helper Functions ──────────────────────────────────────────

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()


def get_vehicle_by_vin(db: Session, vin: str) -> Optional[Vehicle]:
    """Get vehicle by VIN from database."""
    return db.query(Vehicle).filter(Vehicle.vin == vin.upper()).first()


# ─── Routes ──────────────────────────────────────────────────

@router.post("/decode-vin", response_model=VehicleResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def decode_vin(
    request: VinDecodeRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Decode VIN using CarAPI.
    
    **Request Body:**
    - `vin`: Vehicle VIN
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Vehicle details from CarAPI
    - `source`: Data source
    - `error`: Error message if unsuccessful
    """
    try:
        vin = request.vin.upper().strip()
        
        # Validate VIN format
        if not vin_validator.is_valid(vin):
            return VehicleResponse(
                success=False,
                error="Invalid VIN format"
            )
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.decode_vin(vin)
        
        if "error" in result:
            return VehicleResponse(
                success=False,
                error=result["error"]
            )
        
        # Check if vehicle exists in our database
        existing_vehicle = get_vehicle_by_vin(db, vin)
        
        return VehicleResponse(
            success=True,
            data={
                "vehicle": result,
                "in_database": bool(existing_vehicle),
                "database_vehicle": {
                    "id": existing_vehicle.id,
                    "registration_number": existing_vehicle.registration_number,
                    "make": existing_vehicle.make,
                    "model": existing_vehicle.model,
                    "year": existing_vehicle.year,
                } if existing_vehicle else None
            },
            source="CarAPI",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"VIN decode error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.post("/valuation", response_model=VehicleResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_vehicle_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get vehicle valuation using CarAPI and AUTO-V.
    
    **Request Body:**
    - `vin`: Vehicle VIN
    - `make`: Vehicle make (optional)
    - `model`: Vehicle model (optional)
    - `year`: Vehicle year (optional)
    - `odometer`: Vehicle odometer (optional)
    - `condition`: Vehicle condition (optional)
    - `purpose`: Valuation purpose (optional)
    - `region`: Region (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Valuation from CarAPI and AUTO-V with comparison
    - `source`: Data source
    - `error`: Error message if unsuccessful
    """
    try:
        vin = request.vin.upper().strip()
        
        # Validate VIN format
        if not vin_validator.is_valid(vin):
            return VehicleResponse(
                success=False,
                error="Invalid VIN format"
            )
        
        # Get existing vehicle from database
        existing_vehicle = get_vehicle_by_vin(db, vin)
        
        # Use provided data or fallback to database
        make = request.make or (existing_vehicle.make if existing_vehicle else None)
        model = request.model or (existing_vehicle.model if existing_vehicle else None)
        year = request.year or (existing_vehicle.year if existing_vehicle else None)
        odometer = request.odometer or (existing_vehicle.odometer if existing_vehicle else 0)
        
        # Get CarAPI service
        carapi = get_carapi_service()
        carapi_result = carapi.get_valuation(vin)
        
        if "error" in carapi_result:
            return VehicleResponse(
                success=False,
                error=carapi_result["error"]
            )
        
        # Get our own valuation for comparison
        valuation_service = get_valuation_service()
        our_valuation = valuation_service.calculate_valuation({
            'vin': vin,
            'make': make,
            'model': model,
            'year': year,
            'odometer': odometer,
            'condition': request.condition or 'Good',
            'purpose': request.purpose or 'Market Value',
            'region': request.region or 'Nairobi'
        })
        
        carapi_value = carapi_result.get('valuation', {}).get('current_value', 0)
        autov_value = our_valuation.get('market_value', 0)
        
        return VehicleResponse(
            success=True,
            data={
                "carapi_valuation": carapi_result,
                "auto_v_valuation": our_valuation,
                "comparison": {
                    "market_value_carapi": carapi_value,
                    "market_value_autov": autov_value,
                    "difference": abs(carapi_value - autov_value),
                    "difference_percentage": round(
                        abs(carapi_value - autov_value) / max(carapi_value, 1) * 100, 2
                    )
                },
                "vehicle_info": {
                    "make": make,
                    "model": model,
                    "year": year,
                    "odometer": odometer,
                    "in_database": bool(existing_vehicle)
                }
            },
            source="CarAPI + AUTO-V",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Valuation error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.get("/search", response_model=VehicleResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def search_vehicles(
    make: Optional[str] = Query(None, description="Vehicle make"),
    model: Optional[str] = Query(None, description="Vehicle model"),
    year: Optional[int] = Query(None, description="Vehicle year"),
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search for vehicles in database and CarAPI.
    
    **Query Parameters:**
    - `make`: Vehicle make (optional)
    - `model`: Vehicle model (optional)
    - `year`: Vehicle year (optional)
    - `limit`: Number of results (default: 10, max: 50)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Search results
    - `count`: Number of results
    - `source`: Data source
    - `error`: Error message if unsuccessful
    """
    try:
        if not make and not model:
            return VehicleResponse(
                success=False,
                error="At least make or model is required"
            )
        
        # Search in local database first
        query = db.query(Vehicle)
        if make:
            query = query.filter(Vehicle.make.ilike(f"%{make}%"))
        if model:
            query = query.filter(Vehicle.model.ilike(f"%{model}%"))
        if year:
            query = query.filter(Vehicle.year == year)
        
        db_results = query.limit(limit).all()
        
        # Get CarAPI results
        carapi = get_carapi_service()
        carapi_result = carapi.search_vehicles(make, model, year, limit)
        
        if "error" in carapi_result:
            return VehicleResponse(
                success=False,
                error=carapi_result["error"]
            )
        
        return VehicleResponse(
            success=True,
            data={
                "database_results": [
                    {
                        "id": v.id,
                        "registration_number": v.registration_number,
                        "make": v.make,
                        "model": v.model,
                        "year": v.year,
                        "vin": v.vin,
                        "color": v.color,
                        "odometer": v.odometer
                    } for v in db_results
                ],
                "carapi_results": carapi_result,
                "total_db_results": len(db_results)
            },
            count=len(db_results) + len(carapi_result.get('vehicles', [])),
            source="Database + CarAPI",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.post("/photos", response_model=VehicleResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_vehicle_photos(
    request: VehiclePhotosRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get vehicle photos using CarAPI.
    
    **Request Body:**
    - `make`: Vehicle make
    - `model`: Vehicle model
    - `year`: Vehicle year (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Vehicle photos
    - `source`: Data source
    - `error`: Error message if unsuccessful
    """
    try:
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.get_vehicle_photos(request.make, request.model, request.year)
        
        if "error" in result:
            return VehicleResponse(
                success=False,
                error=result["error"]
            )
        
        return VehicleResponse(
            success=True,
            data=result,
            source="CarAPI",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Photos error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.post("/stolen-check", response_model=VehicleResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def check_stolen_vehicle(
    request: VinDecodeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Check if vehicle has been reported stolen.
    
    **Request Body:**
    - `vin`: Vehicle VIN
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Stolen check results
    - `source`: Data source
    - `error`: Error message if unsuccessful
    """
    try:
        vin = request.vin.upper().strip()
        
        # Validate VIN format
        if not vin_validator.is_valid(vin):
            return VehicleResponse(
                success=False,
                error="Invalid VIN format"
            )
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.check_stolen_vehicle(vin)
        
        if "error" in result:
            return VehicleResponse(
                success=False,
                error=result["error"]
            )
        
        return VehicleResponse(
            success=True,
            data=result,
            source="CarAPI",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Stolen check error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.post("/recalls", response_model=VehicleResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_recalls(
    request: RecallsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get vehicle recall records.
    
    **Request Body:**
    - `make`: Vehicle make
    - `model`: Vehicle model
    - `year`: Vehicle year (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Recall records
    - `source`: Data source
    - `error`: Error message if unsuccessful
    """
    try:
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.get_recalls(request.make, request.model, request.year)
        
        if "error" in result:
            return VehicleResponse(
                success=False,
                error=result["error"]
            )
        
        return VehicleResponse(
            success=True,
            data=result,
            source="CarAPI",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Recalls error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.post("/plate-to-vin", response_model=VehicleResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def plate_to_vin(
    request: PlateToVinRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Convert license plate to VIN.
    
    **Request Body:**
    - `plate`: License plate number
    - `country`: Country code (default: us)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: VIN and vehicle details
    - `source`: Data source
    - `error`: Error message if unsuccessful
    """
    try:
        plate = request.plate.upper().strip()
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.plate_to_vin(plate, request.country)
        
        if "error" in result:
            return VehicleResponse(
                success=False,
                error=result["error"]
            )
        
        return VehicleResponse(
            success=True,
            data=result,
            source="CarAPI",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Plate to VIN error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.post("/auto-fill", response_model=VehicleResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def auto_fill_from_vin(
    request: AutoFillRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Auto-fill vehicle details from VIN.
    
    **Request Body:**
    - `vin`: Vehicle VIN
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Auto-filled vehicle details
    - `source`: Data source
    - `error`: Error message if unsuccessful
    """
    try:
        vin = request.vin.upper().strip()
        
        # Validate VIN format
        if not vin_validator.is_valid(vin):
            return VehicleResponse(
                success=False,
                error="Invalid VIN format"
            )
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.decode_vin(vin)
        
        if "error" in result:
            return VehicleResponse(
                success=False,
                error=result["error"]
            )
        
        # Format for AUTO-V
        vehicle_data = {
            "vin": vin,
            "make": result.get("make", ""),
            "model": result.get("model", ""),
            "year": result.get("year"),
            "engine_cc": result.get("engine_cc") or result.get("engine", {}).get("displacement"),
            "transmission": result.get("transmission_type") or result.get("transmission"),
            "fuel_type": result.get("fuel_type"),
            "body_type": result.get("body_type") or result.get("body_style"),
            "drive_type": result.get("drive_type"),
            "doors": result.get("doors"),
            "horsepower": result.get("horsepower") or result.get("engine", {}).get("horsepower"),
            "torque": result.get("torque") or result.get("engine", {}).get("torque"),
            "cylinders": result.get("engine", {}).get("cylinders"),
            "weight": result.get("weight"),
            "color": result.get("color", ""),
            "specs": result
        }
        
        return VehicleResponse(
            success=True,
            data=vehicle_data,
            source="CarAPI",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Auto-fill error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.get("/stats", response_model=VehicleResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_vehicle_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get vehicle statistics.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Statistics from database and CarAPI
    - `error`: Error message if unsuccessful
    """
    try:
        # Get database stats
        total_vehicles = db.query(Vehicle).count()
        total_users = db.query(User).count()
        total_requests = db.query(ServiceRequest).filter(ServiceRequest.service_type == 'valuation').count()
        
        # Get stats by make
        make_stats = db.query(
            Vehicle.make,
            func.count(Vehicle.id).label('count')
        ).group_by(Vehicle.make).all()
        
        # Get CarAPI stats
        carapi = get_carapi_service()
        carapi_stats = carapi.get_stats()
        
        return VehicleResponse(
            success=True,
            data={
                "database": {
                    "total_vehicles": total_vehicles,
                    "total_users": total_users,
                    "total_valuations": total_requests,
                    "by_make": [{"make": m.make, "count": m.count} for m in make_stats]
                },
                "carapi": carapi_stats,
                "timestamp": format_timestamp()
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Stats error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.get("/makes", response_model=VehicleResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_vehicle_makes(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of vehicle makes.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of makes from database and CarAPI
    - `error`: Error message if unsuccessful
    """
    try:
        # Get makes from database
        db_makes = db.query(Vehicle.make).distinct().order_by(Vehicle.make).all()
        db_make_list = [m[0] for m in db_makes if m[0]]
        
        # Get makes from CarAPI
        carapi = get_carapi_service()
        carapi_result = carapi.get_makes()
        
        if "error" in carapi_result:
            return VehicleResponse(
                success=False,
                error=carapi_result["error"]
            )
        
        return VehicleResponse(
            success=True,
            data={
                "database_makes": db_make_list,
                "carapi_makes": carapi_result.get('makes', []),
                "merged": list(set(db_make_list + carapi_result.get('makes', [])))
            },
            source="Database + CarAPI",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get makes error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.get("/models/{make}", response_model=VehicleResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_vehicle_models(
    make: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of vehicle models for a make.
    
    **Path Parameter:**
    - `make`: Vehicle make
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of models from database and CarAPI
    - `error`: Error message if unsuccessful
    """
    try:
        # Get models from database
        db_models = db.query(Vehicle.model).filter(
            Vehicle.make.ilike(f"%{make}%")
        ).distinct().order_by(Vehicle.model).all()
        db_model_list = [m[0] for m in db_models if m[0]]
        
        # Get models from CarAPI
        carapi = get_carapi_service()
        carapi_result = carapi.get_models(make)
        
        if "error" in carapi_result:
            return VehicleResponse(
                success=False,
                error=carapi_result["error"]
            )
        
        return VehicleResponse(
            success=True,
            data={
                "database_models": db_model_list,
                "carapi_models": carapi_result.get('models', []),
                "merged": list(set(db_model_list + carapi_result.get('models', [])))
            },
            source="Database + CarAPI",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get models error: {str(e)}", exc_info=True)
        return VehicleResponse(
            success=False,
            error=str(e)
        )


@router.post("/save", response_model=VehicleResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def save_vehicle(
    vehicle_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save vehicle to database.
    
    **Request Body:**
    - Vehicle data (make, model, year, vin, registration_number, etc.)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Saved vehicle
    - `error`: Error message if unsuccessful
    """
    try:
        # Check if vehicle already exists
        existing = None
        if vehicle_data.get('vin'):
            existing = db.query(Vehicle).filter(
                Vehicle.vin == vehicle_data['vin'].upper()
            ).first()
        elif vehicle_data.get('registration_number'):
            existing = db.query(Vehicle).filter(
                Vehicle.registration_number == vehicle_data['registration_number'].upper()
            ).first()
        
        if existing:
            # Update existing vehicle
            for key, value in vehicle_data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return VehicleResponse(
                success=True,
                data={
                    "id": existing.id,
                    "message": "Vehicle updated successfully"
                },
                source="Database",
                timestamp=format_timestamp()
            )
        else:
            # Create new vehicle
            new_vehicle = Vehicle(
                user_id=current_user.get('id'),
                registration_number=vehicle_data.get('registration_number', '').upper(),
                vin=vehicle_data.get('vin', '').upper(),
                make=vehicle_data.get('make', ''),
                model=vehicle_data.get('model', ''),
                year=vehicle_data.get('year', 0),
                body_type=vehicle_data.get('body_type', ''),
                engine_cc=vehicle_data.get('engine_cc', 0),
                transmission=vehicle_data.get('transmission', ''),
                fuel_type=vehicle_data.get('fuel_type', ''),
                odometer=vehicle_data.get('odometer', 0),
                color=vehicle_data.get('color', ''),
                vehicle_metadata=vehicle_data.get('metadata', {})
            )
            db.add(new_vehicle)
            db.commit()
            db.refresh(new_vehicle)
            return VehicleResponse(
                success=True,
                data={
                    "id": new_vehicle.id,
                    "message": "Vehicle saved successfully"
                },
                source="Database",
                timestamp=format_timestamp()
            )
        
    except Exception as e:
        logger.error(f"Save vehicle error: {str(e)}", exc_info=True)
        db.rollback()
        return VehicleResponse(
            success=False,
            error=str(e)
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
