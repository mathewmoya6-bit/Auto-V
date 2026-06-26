"""
Validation Utilities for AUTO-V
Email, phone, VIN, odometer, amount, date, Kenya ID, KRA PIN, license plate validation
"""

import re
from datetime import datetime
from typing import Optional, Tuple, Union, Dict, Any, List
from pydantic import BaseModel, Field, validator, field_validator

# ─── EMAIL VALIDATION ───────────────────────────────────────────

def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def normalize_email(email: str) -> str:
    """Normalize email address (lowercase, trim)."""
    if not email:
        return ""
    return email.lower().strip()


# ─── PHONE VALIDATION ───────────────────────────────────────────

def validate_phone(phone: str, country: str = "KE") -> bool:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        country: Country code (KE, US, UK, etc.)
    
    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
    
    # Kenya phone validation
    if country.upper() == "KE":
        # Valid formats: 0712345678, 254712345678, +254712345678
        pattern = r'^(0|254|\+254)[17]\d{8}$'
        return bool(re.match(pattern, cleaned))
    
    # Generic validation (at least 10 digits)
    digits = re.sub(r'\D', '', phone)
    return len(digits) >= 10


def normalize_phone(phone: str, country: str = "KE") -> str:
    """
    Normalize phone number to international format.
    
    Args:
        phone: Phone number to normalize
        country: Country code
    
    Returns:
        Normalized phone number
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', phone)
    
    if country.upper() == "KE":
        if cleaned.startswith('0'):
            cleaned = '254' + cleaned[1:]
        elif cleaned.startswith('254'):
            pass
        elif len(cleaned) == 9 and cleaned.startswith('7'):
            cleaned = '254' + cleaned
        elif len(cleaned) == 10 and cleaned.startswith('7'):
            cleaned = '254' + cleaned
    
    return cleaned


# ─── VIN VALIDATION ─────────────────────────────────────────────

def validate_vin(vin: str) -> Tuple[bool, Optional[str]]:
    """
    Validate VIN format and check digit.
    
    Args:
        vin: VIN to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not vin:
        return False, "VIN is empty"
    
    vin = vin.upper().strip()
    
    # Must be 17 characters
    if len(vin) != 17:
        return False, f"VIN must be exactly 17 characters (got {len(vin)})"
    
    # Cannot contain I, O, Q
    if re.search(r'[IOQ]', vin):
        return False, "VIN cannot contain I, O, or Q"
    
    # Must be alphanumeric
    if not vin.isalnum():
        return False, "VIN must be alphanumeric"
    
    # Validate check digit (position 9)
    weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
    transl = {
        'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
        'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
        'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9
    }
    
    try:
        total = sum(transl[char] * weights[i] for i, char in enumerate(vin))
        check_digit = total % 11
        expected = str(check_digit) if check_digit < 10 else 'X'
        
        if vin[8] != expected:
            return False, f"Invalid check digit. Expected: {expected}, got: {vin[8]}"
    except KeyError as e:
        return False, f"Invalid character in VIN: {e}"
    
    return True, None


def validate_vin_format(vin: str) -> bool:
    """Simple VIN format validation without check digit."""
    if not vin:
        return False
    
    vin = vin.upper().strip()
    return (
        len(vin) == 17 and 
        vin.isalnum() and 
        not re.search(r'[IOQ]', vin)
    )


def extract_vin_from_text(text: str) -> Optional[str]:
    """Extract VIN from text using pattern matching."""
    if not text:
        return None
    
    # Look for 17-character alphanumeric pattern
    pattern = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    match = re.search(pattern, text.upper())
    if match:
        return match.group(0)
    
    return None


def get_vin_country(vin: str) -> Optional[str]:
    """
    Get country of origin from VIN (WMI).
    
    Args:
        vin: VIN to check
    
    Returns:
        Country code or None
    """
    if not vin or len(vin) < 3:
        return None
    
    vin = vin.upper().strip()
    wmi = vin[:3]
    
    # WMI country codes
    country_codes = {
        '1': 'US', '2': 'CA', '3': 'MX', '4': 'US', '5': 'US',
        '6': 'AU', '7': 'NZ', '8': 'US', '9': 'US',
        'A': 'US', 'B': 'US', 'C': 'US', 'D': 'US', 'E': 'US',
        'F': 'US', 'G': 'US', 'H': 'US', 'J': 'JP', 'K': 'KR',
        'L': 'CN', 'M': 'IN', 'N': 'IN', 'P': 'PT',
        'R': 'TW', 'S': 'GB', 'T': 'CH', 'U': 'DE',
        'V': 'FR', 'W': 'DE', 'X': 'RU', 'Y': 'BE',
        'Z': 'IT'
    }
    
    return country_codes.get(wmi[0])


# ─── ODOMETER VALIDATION ────────────────────────────────────────

def validate_odometer(value: Union[int, float, str]) -> bool:
    """
    Validate odometer reading.
    
    Args:
        value: Odometer value
    
    Returns:
        True if valid, False otherwise
    """
    try:
        val = float(value)
        return val >= 0 and val <= 1000000  # Max 1,000,000 km
    except (ValueError, TypeError):
        return False


def validate_odometer_trend(
    current: Union[int, float],
    previous: Union[int, float]
) -> bool:
    """
    Validate that current odometer is greater than or equal to previous.
    
    Args:
        current: Current odometer reading
        previous: Previous odometer reading
    
    Returns:
        True if valid, False otherwise
    """
    try:
        return float(current) >= float(previous)
    except (ValueError, TypeError):
        return False


# ─── AMOUNT VALIDATION ──────────────────────────────────────────

def validate_amount(amount: Union[int, float, str]) -> bool:
    """
    Validate monetary amount.
    
    Args:
        amount: Amount to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        val = float(amount)
        return val >= 0 and val <= 100000000  # Max 100,000,000
    except (ValueError, TypeError):
        return False


def validate_positive_amount(amount: Union[int, float, str]) -> bool:
    """Validate that amount is positive (> 0)."""
    try:
        val = float(amount)
        return val > 0 and val <= 100000000
    except (ValueError, TypeError):
        return False


# ─── DATE VALIDATION ────────────────────────────────────────────

def validate_date(date_str: str, format: str = "%Y-%m-%d") -> bool:
    """
    Validate date string format.
    
    Args:
        date_str: Date string to validate
        format: Expected date format
    
    Returns:
        True if valid, False otherwise
    """
    if not date_str:
        return False
    
    try:
        datetime.strptime(date_str, format)
        return True
    except ValueError:
        return False


def validate_date_range(start_date: str, end_date: str) -> bool:
    """
    Validate that start_date is before end_date.
    
    Args:
        start_date: Start date string
        end_date: End date string
    
    Returns:
        True if valid, False otherwise
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        return start <= end
    except ValueError:
        return False


def parse_date(date_str: str, format: str = "%Y-%m-%d") -> Optional[datetime]:
    """Parse date string to datetime object."""
    try:
        return datetime.strptime(date_str, format)
    except ValueError:
        return None


def format_date(date_obj: datetime, format: str = "%Y-%m-%d") -> str:
    """Format datetime object to string."""
    return date_obj.strftime(format)


# ─── KENYA ID VALIDATION ───────────────────────────────────────

def validate_kenya_id(id_number: str) -> bool:
    """
    Validate Kenya ID number.
    
    Args:
        id_number: ID number to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not id_number:
        return False
    
    # Kenyan ID is 8 digits
    return bool(re.match(r'^\d{8}$', id_number))


# ─── KRA PIN VALIDATION ────────────────────────────────────────

def validate_kra_pin(pin: str) -> bool:
    """
    Validate KRA PIN number.
    
    Args:
        pin: KRA PIN to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not pin:
        return False
    
    pin = pin.upper().strip()
    # Format: A123456789A (1 letter + 9 digits + 1 letter)
    return bool(re.match(r'^[A-Z]\d{9}[A-Z]$', pin))


# ─── LICENSE PLATE VALIDATION ──────────────────────────────────

def validate_plate(plate: str, country: str = "KE") -> bool:
    """
    Validate license plate format.
    
    Args:
        plate: License plate to validate
        country: Country code
    
    Returns:
        True if valid, False otherwise
    """
    if not plate:
        return False
    
    plate = plate.upper().strip()
    
    if country.upper() == "KE":
        # Kenya plate formats
        patterns = [
            r'^[A-Z]{3}\s?\d{3}[A-Z]$',    # KCA 123A
            r'^[A-Z]{2}\s?\d{4}[A-Z]$',     # KD 1234A
            r'^[A-Z]{3}\s?\d{3}[A-Z]{2}$',  # KCA 123AA
            r'^[A-Z]{3}\s?\d{4}[A-Z]$',     # KCA 1234A
            r'^[A-Z]{3}\s?\d{3}[A-Z]{3}$',  # KCA 123AAA
        ]
        return any(re.match(p, plate.replace(' ', '')) for p in patterns)
    
    # Generic validation
    return len(plate) >= 5 and len(plate) <= 10


# ─── PYDANTIC VALIDATORS ────────────────────────────────────────

class Validators:
    """Collection of Pydantic validators."""
    
    @staticmethod
    def email(v: str) -> str:
        """Validate email field."""
        if not v:
            return v
        if not validate_email(v):
            raise ValueError(f"Invalid email address: {v}")
        return normalize_email(v)
    
    @staticmethod
    def phone(v: str) -> str:
        """Validate phone field."""
        if not v:
            return v
        if not validate_phone(v):
            raise ValueError(f"Invalid phone number: {v}")
        return normalize_phone(v)
    
    @staticmethod
    def vin(v: str) -> str:
        """Validate VIN field."""
        if not v:
            return v
        is_valid, error = validate_vin(v)
        if not is_valid:
            raise ValueError(error)
        return v.upper().strip()
    
    @staticmethod
    def odometer(v: Union[int, float, str]) -> float:
        """Validate odometer field."""
        if v is None:
            return 0.0
        if not validate_odometer(v):
            raise ValueError(f"Invalid odometer reading: {v}")
        return float(v)
    
    @staticmethod
    def amount(v: Union[int, float, str]) -> float:
        """Validate amount field."""
        if v is None:
            return 0.0
        if not validate_amount(v):
            raise ValueError(f"Invalid amount: {v}")
        return float(v)
    
    @staticmethod
    def positive_amount(v: Union[int, float, str]) -> float:
        """Validate positive amount field."""
        if v is None:
            return 0.0
        if not validate_positive_amount(v):
            raise ValueError(f"Amount must be positive: {v}")
        return float(v)
    
    @staticmethod
    def date(v: str) -> str:
        """Validate date field."""
        if not v:
            return v
        if not validate_date(v):
            raise ValueError(f"Invalid date format: {v}")
        return v
    
    @staticmethod
    def kenya_id(v: str) -> str:
        """Validate Kenya ID field."""
        if not v:
            return v
        if not validate_kenya_id(v):
            raise ValueError(f"Invalid Kenya ID: {v}")
        return v
    
    @staticmethod
    def kra_pin(v: str) -> str:
        """Validate KRA PIN field."""
        if not v:
            return v
        if not validate_kra_pin(v):
            raise ValueError(f"Invalid KRA PIN: {v}")
        return v.upper().strip()
    
    @staticmethod
    def plate(v: str) -> str:
        """Validate license plate field."""
        if not v:
            return v
        if not validate_plate(v):
            raise ValueError(f"Invalid license plate: {v}")
        return v.upper().strip()


# ─── PYDANTIC MODELS ────────────────────────────────────────────

class EmailModel(BaseModel):
    """Model with email validation."""
    email: str = Field(..., description="Email address")
    
    @field_validator('email')
    def validate_email(cls, v: str) -> str:
        return Validators.email(v)


class PhoneModel(BaseModel):
    """Model with phone validation."""
    phone: str = Field(..., description="Phone number")
    
    @field_validator('phone')
    def validate_phone(cls, v: str) -> str:
        return Validators.phone(v)


class VinModel(BaseModel):
    """Model with VIN validation."""
    vin: str = Field(..., description="Vehicle Identification Number")
    
    @field_validator('vin')
    def validate_vin(cls, v: str) -> str:
        return Validators.vin(v)


class AmountModel(BaseModel):
    """Model with amount validation."""
    amount: float = Field(..., description="Amount")
    
    @field_validator('amount')
    def validate_amount(cls, v: float) -> float:
        return Validators.positive_amount(v)


# ─── EXPORTS ─────────────────────────────────────────────────────

__all__ = [
    # Email
    'validate_email',
    'normalize_email',
    
    # Phone
    'validate_phone',
    'normalize_phone',
    
    # VIN
    'validate_vin',
    'validate_vin_format',
    'extract_vin_from_text',
    'get_vin_country',
    
    # Odometer
    'validate_odometer',
    'validate_odometer_trend',
    
    # Amount
    'validate_amount',
    'validate_positive_amount',
    
    # Date
    'validate_date',
    'validate_date_range',
    'parse_date',
    'format_date',
    
    # Kenya
    'validate_kenya_id',
    'validate_kra_pin',
    'validate_plate',
    
    # Pydantic
    'Validators',
    'EmailModel',
    'PhoneModel',
    'VinModel',
    'AmountModel',
]
