# utils/validators.py
import re
from datetime import datetime
from typing import Optional, Tuple, Union

# ─── EMAIL VALIDATION ──────────────────────────────────────

def validate_email(email: str) -> bool:
    """
    Validate email address format
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# ─── PHONE VALIDATION ──────────────────────────────────────

def validate_phone(phone: str, country: str = "KE") -> bool:
    """
    Validate phone number format
    
    Args:
        phone: Phone number to validate
        country: Country code (KE, US, UK, etc.)
        
    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False
    
    # Remove common separators
    phone = re.sub(r'[\s\-\(\)\.]', '', phone)
    
    # Kenya phone validation
    if country.upper() == "KE":
        # Valid formats: 0712345678, 254712345678, +254712345678
        pattern = r'^(0|254|\+254)?[17]\d{8}$'
        return bool(re.match(pattern, phone))
    
    # Generic validation (at least 10 digits)
    digits = re.sub(r'\D', '', phone)
    return len(digits) >= 10

# ─── VIN VALIDATION ────────────────────────────────────────

def validate_vin(vin: str) -> Tuple[bool, Optional[str]]:
    """
    Validate VIN format and check digit
    
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
        return False, "VIN must be exactly 17 characters"
    
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
    except KeyError:
        return False, "Invalid characters in VIN"
    
    return True, None

def validate_vin_format(vin: str) -> bool:
    """Simple VIN format validation without check digit"""
    if not vin:
        return False
    
    vin = vin.upper().strip()
    return len(vin) == 17 and vin.isalnum() and not re.search(r'[IOQ]', vin)

# ─── ODOMETER VALIDATION ──────────────────────────────────

def validate_odometer(value: Union[int, float, str]) -> bool:
    """
    Validate odometer reading
    
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

# ─── AMOUNT VALIDATION ────────────────────────────────────

def validate_amount(amount: Union[int, float, str]) -> bool:
    """
    Validate monetary amount
    
    Args:
        amount: Amount to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        val = float(amount)
        return val > 0 and val <= 100000000  # Max 100,000,000
    except (ValueError, TypeError):
        return False

# ─── DATE VALIDATION ──────────────────────────────────────

def validate_date(date_str: str, format: str = "%Y-%m-%d") -> bool:
    """
    Validate date string format
    
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
    Validate that start_date is before end_date
    
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

# ─── KENYA ID VALIDATION ──────────────────────────────────

def validate_kenya_id(id_number: str) -> bool:
    """
    Validate Kenya ID number
    
    Args:
        id_number: ID number to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not id_number:
        return False
    
    # Kenyan ID is 8 digits
    return bool(re.match(r'^\d{8}$', id_number))

# ─── KRA PIN VALIDATION ───────────────────────────────────

def validate_kra_pin(pin: str) -> bool:
    """
    Validate KRA PIN number
    
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

# ─── LICENSE PLATE VALIDATION ─────────────────────────────

def validate_plate(plate: str, country: str = "KE") -> bool:
    """
    Validate license plate format
    
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
        # Kenya plate formats: KCA 123A, KDA 123B, etc.
        patterns = [
            r'^[A-Z]{3}\s?\d{3}[A-Z]$',  # KCA 123A
            r'^[A-Z]{2}\s?\d{4}[A-Z]$',   # KD 1234A
            r'^[A-Z]{3}\s?\d{3}[A-Z]{2}$' # KCA 123AA
        ]
        return any(re.match(p, plate) for p in patterns)
    
    # Generic validation
    return len(plate) >= 5 and len(plate) <= 10
