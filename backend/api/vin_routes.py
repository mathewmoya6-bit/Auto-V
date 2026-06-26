"""
VIN Routes - FastAPI Version
VIN validation, decoding, OCR extraction, and check digit generation
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from app.core.dependencies import get_current_user, get_current_user_optional
from app.services.vin_validator import vin_validator
from app.services.carapi_service import car_api
from app.services.vin_ocr import vin_ocr
from app.core.rate_limit import rate_limit

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


# ─── Helper Functions ──────────────────────────────────────────

def clean_vin(vin: str) -> str:
    """Clean VIN by removing whitespace and converting to uppercase"""
    return vin.upper().strip()


# ─── Routes ──────────────────────────────────────────────────

@router.post("/validate", response_model=VinResponse)
@rate_limit(limit=100, per=60)
async def validate_vin(request: ValidateVinRequest):
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
        
        return VinResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        logger.error(f"VIN validation error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e)
        )


@router.post("/batch-validate", response_model=VinResponse)
@rate_limit(limit=50, per=60)
async def batch_validate_vin(request: BatchValidateVinRequest):
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
            results.append(result)
        
        return VinResponse(
            success=True,
            data={
                "results": results,
                "count": len(results)
            }
        )
        
    except Exception as e:
        logger.error(f"Batch VIN validation error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e)
        )


@router.post("/suggest-corrections", response_model=VinResponse)
@rate_limit(limit=50, per=60)
async def suggest_corrections(request: SuggestCorrectionsRequest):
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
        
        return VinResponse(
            success=True,
            data={
                "original_vin": vin,
                "suggestions": suggestions
            }
        )
        
    except Exception as e:
        logger.error(f"Correction suggestion error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e)
        )


@router.post("/extract", response_model=VinResponse)
@rate_limit(limit=10, per=60)
async def extract_vin(request: ExtractVinRequest):
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
                car_data = car_api.decode_vin(vin)
                if 'error' not in car_data:
                    result['vehicle_details'] = {
                        'make': car_data.get('make', ''),
                        'model': car_data.get('model', ''),
                        'year': car_data.get('year', ''),
                        'engine': car_data.get('engine', ''),
                        'manufacturer': car_data.get('manufacturer', ''),
                        'country': car_data.get('country', '')
                    }
        
        return VinResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        logger.error(f"VIN extraction error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e)
        )


@router.get("/decode/{vin}", response_model=VinResponse)
@rate_limit(limit=50, per=60)
async def decode_vin(vin: str):
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
                data={"validation": validation}
            )
        
        # Get vehicle details from API
        car_data = car_api.decode_vin(vin)
        
        if 'error' in car_data:
            return VinResponse(
                success=False,
                error="VIN not found in database"
            )
        
        return VinResponse(
            success=True,
            data={
                "vin": vin,
                "validation": validation,
                "vehicle": car_data
            }
        )
        
    except Exception as e:
        logger.error(f"VIN decode error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e)
        )


@router.post("/generate-check-digit", response_model=VinResponse)
@rate_limit(limit=50, per=60)
async def generate_check_digit(request: GenerateCheckDigitRequest):
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
                error="VIN without check digit must be 16 characters"
            )
        
        # Generate check digit
        check_digit = vin_validator.generate_check_digit(vin_without)
        
        # Construct full VIN
        full_vin = vin_without[:8] + check_digit + vin_without[8:]
        
        return VinResponse(
            success=True,
            data={
                "check_digit": check_digit,
                "full_vin": full_vin
            }
        )
        
    except Exception as e:
        logger.error(f"Check digit generation error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e)
        )


@router.get("/country/{wmi}", response_model=VinResponse)
@rate_limit(limit=50, per=60)
async def get_country_by_wmi(wmi: str):
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
                error="WMI not found"
            )
        
        return VinResponse(
            success=True,
            data=country_info
        )
        
    except Exception as e:
        logger.error(f"Country lookup error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e)
        )


@router.get("/manufacturer/{wmi}", response_model=VinResponse)
@rate_limit(limit=50, per=60)
async def get_manufacturer_by_wmi(wmi: str):
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
                error="WMI not found"
            )
        
        return VinResponse(
            success=True,
            data=manufacturer_info
        )
        
    except Exception as e:
        logger.error(f"Manufacturer lookup error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e)
        )


@router.get("/model/{vin}", response_model=VinResponse)
@rate_limit(limit=50, per=60)
async def get_model_details(vin: str):
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
                error="Invalid VIN"
            )
        
        # Get model details
        model_data = car_api.get_model_details(vin)
        
        if 'error' in model_data:
            return VinResponse(
                success=False,
                error="Model details not found"
            )
        
        return VinResponse(
            success=True,
            data=model_data
        )
        
    except Exception as e:
        logger.error(f"Model details error: {str(e)}", exc_info=True)
        return VinResponse(
            success=False,
            error=str(e)
        )
