# utils/phone_utils.py

import re
import logging

logger = logging.getLogger(__name__)

def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to international format (254XXXXXXXX).
    
    Examples:
        0712345678 -> 254712345678
        +254712345678 -> 254712345678
        254712345678 -> 254712345678
    """
    if not phone:
        raise ValueError("Phone number is required")
    
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', phone)
    
    # Handle different formats
    if cleaned.startswith('0'):
        cleaned = '254' + cleaned[1:]
    elif cleaned.startswith('254'):
        pass  # Already in correct format
    elif len(cleaned) == 9 and cleaned.startswith('7'):
        cleaned = '254' + cleaned
    elif len(cleaned) == 10 and cleaned.startswith('7'):
        cleaned = '254' + cleaned
    else:
        raise ValueError(f"Invalid phone number format: {phone}")
    
    # Validate final format
    if not re.match(r'^254[17]\d{8}$', cleaned):
        raise ValueError(f"Invalid phone number after normalization: {cleaned}")
    
    return cleaned


def validate_phone(phone: str) -> bool:
    """Validate if phone number is in correct format."""
    try:
        normalized = normalize_phone(phone)
        return len(normalized) == 12
    except ValueError:
        return False


def format_phone_for_display(phone: str) -> str:
    """Format phone number for display: 0712345678"""
    normalized = normalize_phone(phone)
    if normalized.startswith('254'):
        return '0' + normalized[3:]
    return normalized
