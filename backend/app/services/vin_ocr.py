# services/vin_ocr.py
import os
import logging
import base64
from typing import Dict, Any, Optional
from services.carapi_service import get_carapi_service
from services.vin_validator import vin_validator

logger = logging.getLogger(__name__)

def extract_vin_from_image(image_url: str) -> Dict[str, Any]:
    """
    Extract VIN from image using CarAPI OCR
    
    Args:
        image_url: URL of the vehicle image
        
    Returns:
        Dict with extracted VIN and confidence
    """
    try:
        carapi = get_carapi_service()
        result = carapi.extract_vin_from_image(image_url)
        
        if "error" in result:
            logger.error(f"CarAPI OCR error: {result['error']}")
            return {
                "extracted": False,
                "vin": None,
                "error": result['error'],
                "source": "CarAPI"
            }
        
        # Validate extracted VIN
        vin = result.get('vin', '').upper().strip()
        validation = vin_validator.validate(vin) if vin else {"valid": False}
        
        return {
            "extracted": bool(vin),
            "vin": vin if validation.get("valid") else None,
            "confidence": result.get('confidence', 0.0),
            "model_used": "CarAPI OCR",
            "source": "CarAPI",
            "validation": validation,
            "raw_result": result
        }
        
    except Exception as e:
        logger.error(f"VIN OCR error: {str(e)}", exc_info=True)
        return {
            "extracted": False,
            "vin": None,
            "error": str(e),
            "source": "CarAPI"
        }

# ─── FALLBACK: Basic OCR using pytesseract (if available) ──

def extract_vin_from_image_fallback(image_data: bytes) -> Dict[str, Any]:
    """
    Fallback OCR using pytesseract (if installed)
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Dict with extracted VIN and confidence
    """
    try:
        import pytesseract
        from PIL import Image
        import io
        
        # Open image
        image = Image.open(io.BytesIO(image_data))
        
        # Extract text
        text = pytesseract.image_to_string(image)
        
        # Find VIN in text
        import re
        vin_pattern = r'[A-HJ-NPR-Z0-9]{17}'
        matches = re.findall(vin_pattern, text.upper())
        
        vin = matches[0] if matches else None
        
        if vin:
            validation = vin_validator.validate(vin)
            if not validation.get("valid"):
                vin = None
        
        return {
            "extracted": bool(vin),
            "vin": vin,
            "confidence": 0.7 if vin else 0.0,
            "model_used": "Tesseract OCR (Fallback)",
            "source": "Fallback OCR"
        }
        
    except ImportError:
        return {
            "extracted": False,
            "vin": None,
            "error": "Tesseract OCR not installed",
            "source": "Fallback OCR"
        }
    except Exception as e:
        logger.error(f"Fallback OCR error: {str(e)}")
        return {
            "extracted": False,
            "vin": None,
            "error": str(e),
            "source": "Fallback OCR"
        }

# ─── QUICK TEST ──────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing VIN OCR Service...")
    
    # Test with a sample image URL
    test_url = "https://example.com/vehicle.jpg"
    result = extract_vin_from_image(test_url)
    
    print(f"Extracted: {result.get('extracted')}")
    print(f"VIN: {result.get('vin')}")
    print(f"Source: {result.get('source')}")
    
    print("✅ VIN OCR Service test complete")
