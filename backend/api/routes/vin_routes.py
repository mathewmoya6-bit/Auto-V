"""
VIN Routes - FastAPI Version
VIN scanning, OCR extraction, database validation, fraud detection
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.core.database import supabase
from app.core.dependencies import get_current_user, get_current_user_optional
from app.services.vin_ocr import extract_vin_from_image
from app.services.vin_validation_service import validate_vin_against_db, comprehensive_fraud_check
from app.services.vin_validator import vin_validator
from app.services.carapi_service import car_api
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vin", tags=["VIN"])


# ─── Pydantic Models ──────────────────────────────────────────

class ScanVinRequest(BaseModel):
    """VIN scan request model"""
    image_url: str = Field(..., description="URL of the image containing VIN")
    user_id: Optional[str] = Field(None, description="User ID")
    ip_address: Optional[str] = Field(None, description="IP address for fraud detection")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")


class ValidateVinRequest(BaseModel):
    """VIN validation request model"""
    vin: str = Field(..., description="VIN to validate")
    
    @validator('vin')
    def validate_vin_format(cls, v):
        v = v.upper().strip()
        if len(v) != 17:
            raise ValueError('VIN must be 17 characters')
        return v


class VinScanResponse(BaseModel):
    """VIN scan response model"""
    success: bool
    vin: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None
    fraud_check: Optional[Dict[str, Any]] = None
    vehicle: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


class VinValidationResponse(BaseModel):
    """VIN validation response model"""
    success: bool
    vin: Optional[str] = None
    is_valid: bool = False
    validation: Optional[Dict[str, Any]] = None
    vehicle: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


# ─── Helper Functions ──────────────────────────────────────────

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─── Routes ──────────────────────────────────────────────────

@router.post("/scan", response_model=VinScanResponse)
@rate_limit(limit=10, per=60)
@log_request
@handle_errors
async def scan_vin(
    request: ScanVinRequest,
    req: Request,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Scan VIN from image URL using OCR.
    
    **Request Body:**
    - `image_url`: URL of the image containing VIN
    - `user_id`: User ID (optional)
    - `ip_address`: IP address for fraud detection (optional)
    - `session_id`: Session ID for tracking (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `vin`: Extracted VIN
    - `validation`: Database validation results
    - `fraud_check`: Fraud detection results
    - `vehicle`: Vehicle details (if found)
    - `error`: Error message if unsuccessful
    """
    try:
        image_url = request.image_url
        user_id = request.user_id or (current_user.get("id") if current_user else None)
        ip_address = request.ip_address or get_client_ip(req)
        
        # Extract VIN from image
        ocr_result = extract_vin_from_image(image_url)
        
        if not ocr_result.get('extracted'):
            return VinScanResponse(
                success=False,
                error="Failed to extract VIN from image",
                validation={
                    "match": False,
                    "risk": "HIGH",
                    "reason": "OCR extraction failed"
                },
                timestamp=format_timestamp()
            )
        
        vin = ocr_result.get('vin')
        
        if not vin:
            return VinScanResponse(
                success=False,
                error="No VIN detected in image",
                validation={
                    "match": False,
                    "risk": "HIGH",
                    "reason": "No VIN found"
                },
                timestamp=format_timestamp()
            )
        
        # Validate VIN format
        validation_result = vin_validator.validate(vin)
        
        if not validation_result.get('valid'):
            return VinScanResponse(
                success=False,
                vin=vin,
                error="Invalid VIN format",
                validation={
                    "match": False,
                    "risk": "HIGH",
                    "reason": "Invalid VIN format",
                    "errors": validation_result.get('errors', []),
                    "suggestions": vin_validator.suggest_corrections(vin)
                },
                timestamp=format_timestamp()
            )
        
        # Check against database
        db_validation = validate_vin_against_db(vin)
        
        # Fraud detection
        fraud_check = comprehensive_fraud_check(
            vin=vin,
            user_id=user_id,
            ip_address=ip_address,
            session_id=request.session_id
        )
        
        # Get vehicle details if valid
        vehicle = None
        if db_validation.get('match'):
            vehicle = db_validation.get('vehicle')
            
            # If vehicle found but no details, fetch from CarAPI
            if vehicle and not vehicle.get('make'):
                try:
                    car_data = car_api.decode_vin(vin)
                    if 'error' not in car_data:
                        # Merge data but don't overwrite existing fields
                        for key, value in car_data.items():
                            if not vehicle.get(key):
                                vehicle[key] = value
                except Exception as e:
                    logger.warning(f"CarAPI lookup failed: {str(e)}")
        
        # Save scan record
        if user_id:
            try:
                supabase.save_vin_scan(
                    user_id=user_id,
                    vin=vin,
                    image_url=image_url,
                    status='verified' if db_validation.get('match') else 'pending',
                    ip_address=ip_address,
                    session_id=request.session_id
                )
            except Exception as e:
                logger.warning(f"Failed to save scan record: {str(e)}")
        
        # Determine risk level
        risk_level = "LOW"
        if not db_validation.get('match'):
            risk_level = "MEDIUM"
        if fraud_check.get('risk_score', 0) > 70:
            risk_level = "HIGH"
        
        return VinScanResponse(
            success=True,
            vin=vin,
            validation={
                "match": db_validation.get('match', False),
                "risk": risk_level,
                "database": db_validation,
                "confidence": ocr_result.get('confidence', 0)
            },
            fraud_check=fraud_check,
            vehicle=vehicle,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"VIN scan error: {str(e)}", exc_info=True)
        return VinScanResponse(
            success=False,
            error=str(e)
        )


@router.post("/validate", response_model=VinValidationResponse)
@rate_limit(limit=20, per=60)
@log_request
@handle_errors
async def validate_vin(
    request: ValidateVinRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Validate a VIN against database and format rules.
    
    **Request Body:**
    - `vin`: VIN to validate
    
    **Response:**
    - `success`: Boolean indicating success
    - `vin`: Validated VIN
    - `is_valid`: Whether VIN is valid
    - `validation`: Detailed validation results
    - `vehicle`: Vehicle details (if found)
    - `error`: Error message if unsuccessful
    """
    try:
        vin = request.vin.upper().strip()
        
        # Validate format
        format_validation = vin_validator.validate(vin)
        
        if not format_validation.get('valid'):
            return VinValidationResponse(
                success=False,
                vin=vin,
                is_valid=False,
                validation=format_validation,
                error="Invalid VIN format",
                timestamp=format_timestamp()
            )
        
        # Check against database
        db_validation = validate_vin_against_db(vin)
        
        # Get vehicle details if found
        vehicle = None
        if db_validation.get('match'):
            vehicle = db_validation.get('vehicle')
            
            # If vehicle found but no details, fetch from CarAPI
            if vehicle and not vehicle.get('make'):
                try:
                    car_data = car_api.decode_vin(vin)
                    if 'error' not in car_data:
                        for key, value in car_data.items():
                            if not vehicle.get(key):
                                vehicle[key] = value
                except Exception as e:
                    logger.warning(f"CarAPI lookup failed: {str(e)}")
        
        return VinValidationResponse(
            success=True,
            vin=vin,
            is_valid=True,
            validation={
                "format_valid": True,
                "database_match": db_validation.get('match', False),
                "check_digit": format_validation.get('checks', {}).get('check_digit', False),
                "details": format_validation.get('details', {})
            },
            vehicle=vehicle,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"VIN validation error: {str(e)}", exc_info=True)
        return VinValidationResponse(
            success=False,
            error=str(e)
        )


@router.get("/check/{vin}", response_model=VinValidationResponse)
@rate_limit(limit=20, per=60)
@log_request
@handle_errors
async def check_vin(
    vin: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Quick VIN check (GET method).
    
    **Path Parameter:**
    - `vin`: VIN to check
    
    **Response:**
    - `success`: Boolean indicating success
    - `vin`: Checked VIN
    - `is_valid`: Whether VIN is valid
    - `validation`: Validation results
    - `error`: Error message if unsuccessful
    """
    try:
        vin = vin.upper().strip()
        
        # Validate format
        format_validation = vin_validator.validate(vin)
        
        if not format_validation.get('valid'):
            return VinValidationResponse(
                success=False,
                vin=vin,
                is_valid=False,
                validation=format_validation,
                error="Invalid VIN format",
                timestamp=format_timestamp()
            )
        
        # Check against database
        db_validation = validate_vin_against_db(vin)
        
        return VinValidationResponse(
            success=True,
            vin=vin,
            is_valid=True,
            validation={
                "format_valid": True,
                "database_match": db_validation.get('match', False),
                "details": format_validation.get('details', {})
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"VIN check error: {str(e)}", exc_info=True)
        return VinValidationResponse(
            success=False,
            error=str(e)
        )


@router.get("/history", response_model=VinScanResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_vin_scan_history(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's VIN scan history.
    
    **Query Parameters:**
    - `limit`: Number of results to return (default: 50)
    - `offset`: Number of results to skip (default: 0)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of scans
    - `count`: Total count
    - `error`: Error message if unsuccessful
    """
    try:
        # Get scans from database
        result = supabase.table("vin_scans") \
            .select("*") \
            .eq("user_id", current_user.get("id")) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        
        return VinScanResponse(
            success=True,
            data=result.data,
            count=len(result.data),
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get VIN scan history error: {str(e)}", exc_info=True)
        return VinScanResponse(
            success=False,
            error=str(e)
        )


@router.get("/fraud-check/{vin}", response_model=VinScanResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def fraud_check_vin(
    vin: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Perform comprehensive fraud check on a VIN.
    
    **Path Parameter:**
    - `vin`: VIN to check
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Fraud check results
    - `error`: Error message if unsuccessful
    """
    try:
        vin = vin.upper().strip()
        
        # Validate VIN format
        if not vin_validator.is_valid(vin):
            return VinScanResponse(
                success=False,
                error="Invalid VIN format",
                fraud_check={
                    "risk_score": 100,
                    "risk_level": "HIGH",
                    "issues": ["Invalid VIN format"]
                },
                timestamp=format_timestamp()
            )
        
        # Perform fraud check
        fraud_check = comprehensive_fraud_check(
            vin=vin,
            user_id=current_user.get("id"),
            ip_address=None
        )
        
        return VinScanResponse(
            success=True,
            vin=vin,
            fraud_check=fraud_check,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Fraud check error: {str(e)}", exc_info=True)
        return VinScanResponse(
            success=False,
            error=str(e)
        )


@router.get("/statistics", response_model=VinScanResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_vin_statistics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get VIN scan statistics.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Statistics
    - `error`: Error message if unsuccessful
    """
    try:
        # Get all scans for user
        result = supabase.table("vin_scans") \
            .select("*") \
            .eq("user_id", current_user.get("id")) \
            .execute()
        
        scans = result.data
        
        total = len(scans)
        verified = len([s for s in scans if s.get("status") == "verified"])
        pending = len([s for s in scans if s.get("status") == "pending"])
        failed = len([s for s in scans if s.get("status") == "failed"])
        
        # Get unique VINs
        unique_vins = len(set(s.get("vin") for s in scans if s.get("vin")))
        
        return VinScanResponse(
            success=True,
            data={
                "total_scans": total,
                "verified": verified,
                "pending": pending,
                "failed": failed,
                "unique_vins": unique_vins,
                "success_rate": round((verified / total * 100) if total > 0 else 0, 2)
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"VIN statistics error: {str(e)}", exc_info=True)
        return VinScanResponse(
            success=False,
            error=str(e)
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
