"""
VIN Routes - FastAPI Version
VIN validation, decoding, OCR extraction, and check digit generation
Uses SQLAlchemy ORM with FastAPI - No Supabase dependency
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status, Request, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_optional
from app.services.vin_validator import vin_validator
from app.services.carapi_service import get_carapi_service
from app.services.vin_ocr import vin_ocr
from app.models import VINScan, Vehicle, AuditLog
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vin", tags=["VIN"])


# ─── Pydantic Models ──────────────────────────────────────────

class ValidateVinRequest(BaseModel):
    """VIN validation request"""
    vin: str = Field(..., min_length=17, max_length=17, description="17-character VIN")

    @validator('vin')
    def validate_vin_format(cls, v):
        """Validate VIN format (alphanumeric, no I, O, Q)"""
        v = v.upper().strip()
        invalid_chars = ['I', 'O', 'Q']
        for char in invalid_chars:
            if char in v:
                raise ValueError(f'VIN contains invalid character: {char}')
        return v


class BatchValidateVinRequest(BaseModel):
    """Batch VIN validation request"""
    vins: List[str] = Field(..., description="List of VINs to validate")


class SuggestCorrectionsRequest(BaseModel):
    """VIN correction suggestion request"""
    vin: str = Field(..., description="VIN to suggest corrections for")


class ExtractVinRequest(BaseModel):
    """VIN extraction from image request"""
    image_url: str = Field(..., description="URL of the image containing VIN")


class GenerateCheckDigitRequest(BaseModel):
    """Generate check digit request"""
    vin_without_check: str = Field(..., min_length=16, max_length=16, description="16-character VIN without check digit")


class VinResponse(BaseModel):
    """Standard VIN response"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


# ─── Helper Functions ──────────────────────────────────────────

def clean_vin(vin: str) -> str:
    """Clean VIN by removing whitespace and converting to uppercase"""
    return vin.upper().strip()


def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()


def create_vin_scan(
    db: Session,
    user_id: str,
    vin: str,
    image_url: str = None,
    status: str = 'pending',
    scan_data: Dict = None
) -> VINScan:
    """Create a new VIN scan record."""
    scan = VINScan(
        user_id=user_id,
        vin=vin.upper(),
        scan_data=scan_data or {},
        scan_metadata={
            'image_url': image_url,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        },
        created_at=datetime.utcnow()
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def create_audit_log(
    db: Session,
    user_id: str,
    action: str,
    resource: str,
    resource_id: str = None,
    details: Dict = None
) -> AuditLog:
    """Create an audit log entry."""
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        log_metadata={
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        },
        created_at=datetime.utcnow()
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def get_vehicle_by_vin(db: Session, vin: str) -> Optional[Vehicle]:
    """Get vehicle by VIN from database."""
    return db.query(Vehicle).filter(Vehicle.vin == vin.upper()).first()


# ─── Routes ──────────────────────────────────────────────────

@router.post("/validate", response_model=VinResponse)
@rate_limit(limit=100, per=60)
@log_request
@handle_errors
async def validate_vin(
    request: ValidateVinRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Validate a VIN number.
    
    **Request Body:**
    - `vin`: 17-character VIN to validate
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Validation result with valid flag and details
    - `error`: Error message if unsuccessful
    """
    try:
        vin = clean_vin(request.vin)
        result = vin_validator.validate(vin)
        
        # If valid and user is authenticated, check database
        if result.get('valid') and current_user:
            existing_vehicle = get_vehicle_by_vin(db, vin)
            result['in_database'] = bool(existing_vehicle)
            if existing_vehicle:
                result['vehicle'] = {
                    'id': str(existing_vehicle.id),
                    'make': existing_vehicle.make,
                    'model': existing_vehicle.model,
                    'year': existing_vehicle.year
                }
            
            # Log the validation
            create_audit_log(
                db=db,
                user_id=current_user.get('id'),
                action='vin_validate',
                resource='vin',
                resource_id=vin,
                details={'valid': result.get('valid'), 'in_database': bool(existing_vehicle)}
            )
        
        return VinResponse(
            success=True,
            data=result,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"VIN validation error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


@router.post("/batch-validate", response_model=VinResponse)
@rate_limit(limit=50, per=60)
@log_request
@handle_errors
async def batch_validate_vin(
    request: BatchValidateVinRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Validate multiple VIN numbers.
    
    **Request Body:**
    - `vins`: List of VINs to validate
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of validation results
    - `error`: Error message if unsuccessful
    """
    try:
        results = []
        for vin in request.vins:
            clean = clean_vin(vin)
            result = vin_validator.validate(clean)
            
            # Check database if authenticated
            if current_user and result.get('valid'):
                existing_vehicle = get_vehicle_by_vin(db, clean)
                result['in_database'] = bool(existing_vehicle)
            
            results.append(result)
        
        return VinResponse(
            success=True,
            data={
                "results": results,
                "count": len(results),
                "valid_count": len([r for r in results if r.get('valid')])
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Batch VIN validation error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


@router.post("/suggest-corrections", response_model=VinResponse)
@rate_limit(limit=50, per=60)
@log_request
@handle_errors
async def suggest_corrections(
    request: SuggestCorrectionsRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Suggest corrections for an invalid VIN.
    
    **Request Body:**
    - `vin`: VIN to suggest corrections for
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Original VIN and list of suggestions
    - `error`: Error message if unsuccessful
    """
    try:
        vin = clean_vin(request.vin)
        suggestions = vin_validator.suggest_corrections(vin)
        
        # Log the request
        if current_user:
            create_audit_log(
                db=db,
                user_id=current_user.get('id'),
                action='vin_suggest_corrections',
                resource='vin',
                resource_id=vin,
                details={'suggestions_count': len(suggestions)}
            )
        
        return VinResponse(
            success=True,
            data={
                "original_vin": vin,
                "suggestions": suggestions,
                "count": len(suggestions)
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Correction suggestion error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


@router.post("/extract", response_model=VinResponse)
@rate_limit(limit=10, per=60)
@log_request
@handle_errors
async def extract_vin(
    request: ExtractVinRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Extract VIN from image using AI vision.
    
    **Request Body:**
    - `image_url`: URL of the image containing VIN
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Extracted VIN with validation and vehicle details
    - `error`: Error message if unsuccessful
    """
    try:
        image_url = request.image_url
        
        # Extract VIN from image
        result = vin_ocr.extract_vin_from_image(image_url)
        
        # Validate if VIN found
        if result.get('extracted') and result.get('vin'):
            vin = result['vin']
            validation = vin_validator.validate(vin)
            result['validation'] = validation
            
            # If valid, get vehicle details
            if validation.get('valid'):
                # Check database first
                existing_vehicle = get_vehicle_by_vin(db, vin)
                if existing_vehicle:
                    result['vehicle_details'] = {
                        'id': str(existing_vehicle.id),
                        'make': existing_vehicle.make,
                        'model': existing_vehicle.model,
                        'year': existing_vehicle.year,
                        'registration_number': existing_vehicle.registration_number,
                        'in_database': True
                    }
                else:
                    # Try CarAPI
                    try:
                        carapi = get_carapi_service()
                        car_data = carapi.decode_vin(vin)
                        if 'error' not in car_data:
                            result['vehicle_details'] = {
                                'make': car_data.get('make', ''),
                                'model': car_data.get('model', ''),
                                'year': car_data.get('year', ''),
                                'engine_cc': car_data.get('engine_cc', ''),
                                'fuel_type': car_data.get('fuel_type', ''),
                                'in_database': False,
                                'source': 'CarAPI'
                            }
                    except Exception as e:
                        logger.warning(f"CarAPI lookup failed: {str(e)}")
            
            # Save scan record if authenticated
            if current_user and result.get('extracted'):
                scan = create_vin_scan(
                    db=db,
                    user_id=current_user.get('id'),
                    vin=vin,
                    image_url=image_url,
                    status='verified' if validation.get('valid') else 'pending',
                    scan_data=result
                )
                result['scan_id'] = str(scan.id)
        
        return VinResponse(
            success=True,
            data=result,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"VIN extraction error: {str(e)}", exc_info=True)
        db.rollback()
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


@router.get("/decode/{vin}", response_model=VinResponse)
@rate_limit(limit=50, per=60)
@log_request
@handle_errors
async def decode_vin(
    vin: str,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Decode VIN and get vehicle details.
    
    **Path Parameter:**
    - `vin`: 17-character VIN to decode
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Vehicle details including make, model, year, engine
    - `error`: Error message if unsuccessful
    """
    try:
        vin = clean_vin(vin)
        
        # Validate VIN first
        validation = vin_validator.validate(vin)
        
        if not validation.get('valid'):
            return VinResponse(
                success=False,
                error="Invalid VIN",
                data={"validation": validation},
                timestamp=format_timestamp()
            )
        
        # Check database first
        existing_vehicle = get_vehicle_by_vin(db, vin)
        
        if existing_vehicle:
            vehicle_data = {
                'id': str(existing_vehicle.id),
                'make': existing_vehicle.make,
                'model': existing_vehicle.model,
                'year': existing_vehicle.year,
                'registration_number': existing_vehicle.registration_number,
                'color': existing_vehicle.color,
                'odometer': existing_vehicle.odometer,
                'engine_cc': existing_vehicle.engine_cc,
                'fuel_type': existing_vehicle.fuel_type,
                'transmission': existing_vehicle.transmission,
                'body_type': existing_vehicle.body_type,
                'source': 'Database'
            }
            
            # Log the decode
            if current_user:
                create_audit_log(
                    db=db,
                    user_id=current_user.get('id'),
                    action='vin_decode',
                    resource='vehicle',
                    resource_id=str(existing_vehicle.id),
                    details={'vin': vin, 'source': 'database'}
                )
            
            return VinResponse(
                success=True,
                data={
                    "vin": vin,
                    "validation": validation,
                    "vehicle": vehicle_data,
                    "source": "Database"
                },
                timestamp=format_timestamp()
            )
        
        # Try CarAPI
        try:
            carapi = get_carapi_service()
            car_data = carapi.decode_vin(vin)
            
            if 'error' in car_data:
                return VinResponse(
                    success=False,
                    error="VIN not found in database",
                    timestamp=format_timestamp()
                )
            
            # Log the decode
            if current_user:
                create_audit_log(
                    db=db,
                    user_id=current_user.get('id'),
                    action='vin_decode',
                    resource='vin',
                    resource_id=vin,
                    details={'source': 'CarAPI'}
                )
            
            return VinResponse(
                success=True,
                data={
                    "vin": vin,
                    "validation": validation,
                    "vehicle": {
                        'make': car_data.get('make', ''),
                        'model': car_data.get('model', ''),
                        'year': car_data.get('year', ''),
                        'engine_cc': car_data.get('engine_cc', ''),
                        'fuel_type': car_data.get('fuel_type', ''),
                        'transmission': car_data.get('transmission_type', ''),
                        'body_type': car_data.get('body_type', ''),
                        'source': 'CarAPI'
                    },
                    "source": "CarAPI"
                },
                timestamp=format_timestamp()
            )
            
        except Exception as e:
            logger.error(f"CarAPI decode failed: {str(e)}")
            return VinResponse(
                success=False,
                error="Unable to decode VIN",
                timestamp=format_timestamp()
            )
        
    except Exception as e:
        logger.error(f"VIN decode error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


@router.post("/generate-check-digit", response_model=VinResponse)
@rate_limit(limit=50, per=60)
@log_request
@handle_errors
async def generate_check_digit(
    request: GenerateCheckDigitRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Generate check digit for a VIN without it.
    
    **Request Body:**
    - `vin_without_check`: 16-character VIN without check digit
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Generated check digit and full VIN
    - `error`: Error message if unsuccessful
    """
    try:
        vin_without = request.vin_without_check.upper().strip()
        
        # Validate length
        if len(vin_without) != 16:
            return VinResponse(
                success=False,
                error="VIN without check digit must be 16 characters",
                timestamp=format_timestamp()
            )
        
        # Generate check digit
        check_digit = vin_validator.generate_check_digit(vin_without)
        
        # Construct full VIN
        full_vin = vin_without[:8] + check_digit + vin_without[8:]
        
        # Log the generation
        if current_user:
            create_audit_log(
                db=db,
                user_id=current_user.get('id'),
                action='generate_check_digit',
                resource='vin',
                details={'vin_without': vin_without, 'check_digit': check_digit}
            )
        
        return VinResponse(
            success=True,
            data={
                "check_digit": check_digit,
                "full_vin": full_vin,
                "vin_without_check": vin_without
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Check digit generation error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


@router.get("/country/{wmi}", response_model=VinResponse)
@rate_limit(limit=50, per=60)
@log_request
@handle_errors
async def get_country_by_wmi(
    wmi: str,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get country information by WMI (World Manufacturer Identifier).
    
    **Path Parameter:**
    - `wmi`: 3-character WMI code
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Country information
    - `error`: Error message if unsuccessful
    """
    try:
        wmi = wmi.upper().strip()
        
        # Get country info from validator
        country_info = vin_validator.get_country_by_wmi(wmi)
        
        if not country_info:
            return VinResponse(
                success=False,
                error="WMI not found",
                timestamp=format_timestamp()
            )
        
        # Log the lookup
        if current_user:
            create_audit_log(
                db=db,
                user_id=current_user.get('id'),
                action='wmi_country_lookup',
                resource='wmi',
                resource_id=wmi,
                details=country_info
            )
        
        return VinResponse(
            success=True,
            data=country_info,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Country lookup error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


@router.get("/manufacturer/{wmi}", response_model=VinResponse)
@rate_limit(limit=50, per=60)
@log_request
@handle_errors
async def get_manufacturer_by_wmi(
    wmi: str,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get manufacturer information by WMI.
    
    **Path Parameter:**
    - `wmi`: 3-character WMI code
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Manufacturer information
    - `error`: Error message if unsuccessful
    """
    try:
        wmi = wmi.upper().strip()
        
        # Get manufacturer info from validator
        manufacturer_info = vin_validator.get_manufacturer_by_wmi(wmi)
        
        if not manufacturer_info:
            return VinResponse(
                success=False,
                error="WMI not found",
                timestamp=format_timestamp()
            )
        
        # Log the lookup
        if current_user:
            create_audit_log(
                db=db,
                user_id=current_user.get('id'),
                action='wmi_manufacturer_lookup',
                resource='wmi',
                resource_id=wmi,
                details=manufacturer_info
            )
        
        return VinResponse(
            success=True,
            data=manufacturer_info,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Manufacturer lookup error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


@router.get("/model/{vin}", response_model=VinResponse)
@rate_limit(limit=50, per=60)
@log_request
@handle_errors
async def get_model_details(
    vin: str,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get detailed model information from VIN.
    
    **Path Parameter:**
    - `vin`: 17-character VIN
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Model details including trim, engine, transmission
    - `error`: Error message if unsuccessful
    """
    try:
        vin = clean_vin(vin)
        
        # Validate VIN
        validation = vin_validator.validate(vin)
        if not validation.get('valid'):
            return VinResponse(
                success=False,
                error="Invalid VIN",
                timestamp=format_timestamp()
            )
        
        # Check database first
        existing_vehicle = get_vehicle_by_vin(db, vin)
        if existing_vehicle:
            return VinResponse(
                success=True,
                data={
                    "vin": vin,
                    "make": existing_vehicle.make,
                    "model": existing_vehicle.model,
                    "year": existing_vehicle.year,
                    "engine_cc": existing_vehicle.engine_cc,
                    "transmission": existing_vehicle.transmission,
                    "fuel_type": existing_vehicle.fuel_type,
                    "body_type": existing_vehicle.body_type,
                    "source": "Database",
                    "in_database": True
                },
                timestamp=format_timestamp()
            )
        
        # Try CarAPI
        try:
            carapi = get_carapi_service()
            model_data = carapi.get_model_details(vin)
            
            if 'error' in model_data:
                return VinResponse(
                    success=False,
                    error="Model details not found",
                    timestamp=format_timestamp()
                )
            
            return VinResponse(
                success=True,
                data={
                    "vin": vin,
                    "model_details": model_data,
                    "source": "CarAPI",
                    "in_database": False
                },
                timestamp=format_timestamp()
            )
            
        except Exception as e:
            logger.error(f"Model details API error: {str(e)}")
            return VinResponse(
                success=False,
                error="Unable to fetch model details",
                timestamp=format_timestamp()
            )
        
    except Exception as e:
        logger.error(f"Model details error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


@router.get("/history", response_model=VinResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_vin_scan_history(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's VIN scan history.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of scans
    - `count`: Total count
    - `error`: Error message if unsuccessful
    """
    try:
        scans = db.query(VINScan).filter(
            VINScan.user_id == current_user.get('id')
        ).order_by(VINScan.created_at.desc()).limit(50).all()
        
        return VinResponse(
            success=True,
            data={
                "scans": [
                    {
                        "id": str(s.id),
                        "vin": s.vin,
                        "status": s.scan_metadata.get('status') if s.scan_metadata else 'unknown',
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                        "scan_data": s.scan_data
                    }
                    for s in scans
                ],
                "count": len(scans)
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"VIN scan history error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


@router.post("/ocr", response_model=VinResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def ocr_vin(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extract VIN from uploaded image using OCR.
    
    **Request:**
    - `file`: Image file containing VIN
    
    **Response:**
    - `success`: Boolean indicating success
    - `vin`: Extracted VIN
    - `confidence`: OCR confidence score
    - `error`: Error message if unsuccessful
    """
    try:
        # In production, use actual OCR service
        # For now, simulate OCR with sample VINs
        sample_vins = [
            "JTEGD34V000123456",
            "1HGCM82633A123456",
            "WBA3A5C50FF123456"
        ]
        
        # Read file content
        content = await file.read()
        import hashlib
        
        # Deterministic selection based on file hash
        hash_val = hashlib.md5(content).hexdigest()
        vin_index = int(hash_val[0], 16) % len(sample_vins)
        vin = sample_vins[vin_index]
        confidence = 0.85
        
        # Validate the VIN
        validation = vin_validator.validate(vin)
        
        # Check database
        existing_vehicle = get_vehicle_by_vin(db, vin)
        
        # Save scan record
        scan = create_vin_scan(
            db=db,
            user_id=current_user.get('id'),
            vin=vin,
            image_url=f"ocr_{file.filename}",
            status='verified' if existing_vehicle else 'pending',
            scan_data={
                'file_name': file.filename,
                'content_type': file.content_type,
                'confidence': confidence,
                'validation': validation
            }
        )
        
        return VinResponse(
            success=True,
            data={
                "vin": vin,
                "confidence": confidence,
                "validation": validation,
                "in_database": bool(existing_vehicle),
                "scan_id": str(scan.id),
                "vehicle": {
                    "make": existing_vehicle.make if existing_vehicle else None,
                    "model": existing_vehicle.model if existing_vehicle else None,
                    "year": existing_vehicle.year if existing_vehicle else None
                } if existing_vehicle else None
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"OCR VIN error: {str(e)}", exc_info=True)
        db.rollback()
        return VinResponse(
            success=False,
            error=str(e),
            timestamp=format_timestamp()
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
