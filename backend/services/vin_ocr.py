# backend/services/vin_ocr.py
import os
import json
import re
import logging
from typing import Optional, Dict, Any
from openai import OpenAI
from config import config

logger = logging.getLogger(__name__)

class VinOCRService:
    def __init__(self):
        # Secure: Get from config, not hardcoded
        self.api_key = config.OPENAI_API_KEY
        
        if not self.api_key:
            logger.error("OPENAI_API_KEY not configured!")
            raise ValueError("OPENAI_API_KEY is required")
        
        # Initialize client with secure key
        self.client = OpenAI(api_key=self.api_key)
        self.supported_models = ["gpt-4o", "gpt-4-vision-preview", "gpt-4-turbo"]
        self.current_model = "gpt-4o"
        self.cache = {}
        self.cache_ttl = 3600
        
        logger.info("VIN OCR Service initialized securely")
    
    def extract_vin_from_image(self, image_url: str) -> Dict[str, Any]:
        """Extract VIN from image using OpenAI Vision API"""
        try:
            # Securely call OpenAI API
            response = self.client.chat.completions.create(
                model=self.current_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract the 17-character VIN number from this vehicle image."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What is the VIN number?"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=50,
                temperature=0.0
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            vin = self._extract_vin_from_text(content)
            
            return {
                "vin": vin,
                "extracted": vin is not None,
                "model_used": self.current_model,
                "valid_vin": self._validate_vin(vin) if vin else False
            }
            
        except Exception as e:
            logger.error(f"VIN extraction error: {str(e)}")
            return {
                "vin": None,
                "extracted": False,
                "error": str(e)
            }
    
    def _validate_vin(self, vin: str) -> bool:
        """Validate VIN format"""
        if not vin or len(vin) != 17:
            return False
        
        # Check for invalid characters (I, O, Q)
        invalid_chars = ['I', 'O', 'Q']
        if any(char in vin for char in invalid_chars):
            return False
        
        return vin.isalnum()
    
    def _extract_vin_from_text(self, text: str) -> Optional[str]:
        """Extract VIN using regex"""
        import re
        # Clean text
        cleaned = re.sub(r'[^A-Za-z0-9]', '', text)
        
        # Find 17-character pattern
        pattern = r'[A-HJ-NPR-Z0-9]{17}'
        matches = re.findall(pattern, cleaned.upper())
        
        return matches[0] if matches else None

# Initialize service
vin_ocr = VinOCRService()
