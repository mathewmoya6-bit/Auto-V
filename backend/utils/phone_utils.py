"""
Phone Number Utilities for AUTO-V
Validation, normalization, and formatting for Kenyan phone numbers
Supports M-Pesa integration
"""

import re
import logging
from typing import Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

# ─── Constants ──────────────────────────────────────────────────

# Kenyan network prefixes
NETWORK_PREFIXES = {
    'Safaricom': ['071', '072', '073', '0740', '0741', '0742', '0743', '0744', '0745', '0746', '0747', '0748', '0749', '075', '076', '077', '078', '079'],
    'Airtel': ['070', '0711', '0731', '0732', '0733', '0734', '0735', '0736', '0737', '0738', '0739'],
    'Telkom': ['0777', '0787', '0797', '0717'],
    'Equitel': ['0763', '0764', '0765', '0766', '0767', '0768', '0769'],
    'Finserve': ['0701', '0702', '0703', '0704', '0705', '0706', '0707', '0708', '0709'],
}

# Valid prefixes regex pattern
VALID_PREFIXES = [
    '071', '072', '073', '074', '075', '076', '077', '078', '079',
    '070', '0711', '0731', '0732', '0733', '0734', '0735', '0736', '0737', '0738', '0739',
    '0777', '0787', '0797', '0717',
    '0763', '0764', '0765', '0766', '0767', '0768', '0769',
    '0701', '0702', '0703', '0704', '0705', '0706', '0707', '0708', '0709'
]

# Compile regex pattern for validation
PHONE_PATTERN = re.compile(r'^(?:0|\+254|254)?(7\d{8}|1\d{8})$')
FULL_PHONE_PATTERN = re.compile(r'^(254)(7\d{8}|1\d{8})$')


# ─── Phone Number Class ─────────────────────────────────────────

class PhoneNumber:
    """
    Phone number class with validation and formatting methods.
    
    Usage:
        phone = PhoneNumber("0712345678")
        print(phone.normalized)  # 254712345678
        print(phone.display)     # 0712345678
        print(phone.network)     # Safaricom
    """
    
    def __init__(self, phone: str):
        self.raw = phone
        self._normalized = None
        self._display = None
        self._network = None
        self._is_valid = False
        self._validate_and_parse()
    
    def _validate_and_parse(self):
        """Validate and parse the phone number."""
        try:
            # Clean and normalize
            cleaned = self._clean_phone(self.raw)
            normalized = self._normalize_phone(cleaned)
            
            # Validate
            if not self._validate_format(normalized):
                self._is_valid = False
                return
            
            self._normalized = normalized
            self._display = self._format_for_display(normalized)
            self._network = self._detect_network(normalized)
            self._is_valid = True
            
        except Exception as e:
            logger.debug(f"Phone validation failed for {self.raw}: {e}")
            self._is_valid = False
    
    @staticmethod
    def _clean_phone(phone: str) -> str:
        """Remove all non-digit characters."""
        return re.sub(r'\D', '', phone)
    
    @staticmethod
    def _normalize_phone(cleaned: str) -> str:
        """Normalize to 254XXXXXXXX format."""
        if not cleaned:
            raise ValueError("Phone number is required")
        
        # Remove leading + if present
        if cleaned.startswith('+'):
            cleaned = cleaned[1:]
        
        # Handle different formats
        if cleaned.startswith('0'):
            normalized = '254' + cleaned[1:]
        elif cleaned.startswith('254'):
            normalized = cleaned
        elif len(cleaned) == 9 and cleaned.startswith('7'):
            normalized = '254' + cleaned
        elif len(cleaned) == 10 and cleaned.startswith('7'):
            normalized = '254' + cleaned
        else:
            raise ValueError(f"Invalid phone number format: {cleaned}")
        
        return normalized
    
    @staticmethod
    def _validate_format(normalized: str) -> bool:
        """Validate normalized phone number format."""
        if not normalized:
            return False
        
        # Must be 12 digits starting with 254
        if len(normalized) != 12:
            return False
        
        if not normalized.startswith('254'):
            return False
        
        # Check if it matches valid pattern
        if not FULL_PHONE_PATTERN.match(normalized):
            return False
        
        return True
    
    @staticmethod
    def _format_for_display(normalized: str) -> str:
        """Format for display: 0712345678"""
        if normalized.startswith('254'):
            return '0' + normalized[3:]
        return normalized
    
    @staticmethod
    def _detect_network(normalized: str) -> str:
        """Detect network operator from phone number."""
        if not normalized.startswith('254'):
            return 'Unknown'
        
        # Get local format for prefix detection
        local = '0' + normalized[3:]
        
        # Check each network
        for network, prefixes in NETWORK_PREFIXES.items():
            for prefix in prefixes:
                if local.startswith(prefix):
                    return network
        
        return 'Unknown'
    
    @property
    def normalized(self) -> Optional[str]:
        """Get normalized phone number (254XXXXXXXX)."""
        return self._normalized
    
    @property
    def display(self) -> Optional[str]:
        """Get display format (0712345678)."""
        return self._display
    
    @property
    def network(self) -> str:
        """Get network operator name."""
        return self._network or 'Unknown'
    
    @property
    def is_valid(self) -> bool:
        """Check if phone number is valid."""
        return self._is_valid
    
    @property
    def is_safaricom(self) -> bool:
        """Check if phone number is on Safaricom network."""
        return self._network == 'Safaricom'
    
    @property
    def is_airtel(self) -> bool:
        """Check if phone number is on Airtel network."""
        return self._network == 'Airtel'
    
    @property
    def is_telkom(self) -> bool:
        """Check if phone number is on Telkom network."""
        return self._network == 'Telkom'
    
    @property
    def is_equitel(self) -> bool:
        """Check if phone number is on Equitel network."""
        return self._network == 'Equitel'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'raw': self.raw,
            'normalized': self._normalized,
            'display': self._display,
            'network': self._network,
            'is_valid': self._is_valid,
        }
    
    def __str__(self) -> str:
        return self.display or self.raw
    
    def __repr__(self) -> str:
        return f"PhoneNumber('{self.raw}')"


# ─── Core Functions ─────────────────────────────────────────────

def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to international format (254XXXXXXXX).
    
    Examples:
        0712345678 -> 254712345678
        +254712345678 -> 254712345678
        254712345678 -> 254712345678
    
    Args:
        phone: Phone number string
    
    Returns:
        Normalized phone number (254XXXXXXXX)
    
    Raises:
        ValueError: If phone number is invalid
    """
    if not phone:
        raise ValueError("Phone number is required")
    
    phone_obj = PhoneNumber(phone)
    if not phone_obj.is_valid:
        raise ValueError(f"Invalid phone number: {phone}")
    
    return phone_obj.normalized


def validate_phone(phone: str) -> bool:
    """
    Validate if phone number is in correct format.
    
    Args:
        phone: Phone number string
    
    Returns:
        True if valid, False otherwise
    """
    try:
        phone_obj = PhoneNumber(phone)
        return phone_obj.is_valid
    except Exception:
        return False


def format_phone_for_display(phone: str) -> str:
    """
    Format phone number for display: 0712345678.
    
    Args:
        phone: Phone number string
    
    Returns:
        Display formatted phone number
    """
    phone_obj = PhoneNumber(phone)
    if not phone_obj.is_valid:
        return phone
    return phone_obj.display


def detect_network(phone: str) -> str:
    """
    Detect network operator from phone number.
    
    Args:
        phone: Phone number string
    
    Returns:
        Network name (Safaricom, Airtel, Telkom, Equitel, Unknown)
    """
    phone_obj = PhoneNumber(phone)
    return phone_obj.network


def get_phone_info(phone: str) -> Dict[str, Any]:
    """
    Get comprehensive phone number information.
    
    Args:
        phone: Phone number string
    
    Returns:
        Dictionary with phone number details
    """
    phone_obj = PhoneNumber(phone)
    return phone_obj.to_dict()


def is_safaricom(phone: str) -> bool:
    """Check if phone number is on Safaricom network."""
    phone_obj = PhoneNumber(phone)
    return phone_obj.is_safaricom


def is_airtel(phone: str) -> bool:
    """Check if phone number is on Airtel network."""
    phone_obj = PhoneNumber(phone)
    return phone_obj.is_airtel


def is_telkom(phone: str) -> bool:
    """Check if phone number is on Telkom network."""
    phone_obj = PhoneNumber(phone)
    return phone_obj.is_telkom


# ─── Pydantic Validator ─────────────────────────────────────────

def validate_phone_field(v: str) -> str:
    """
    Pydantic validator for phone number fields.
    
    Usage:
        class User(BaseModel):
            phone: str = Field(..., validator=validate_phone_field)
    """
    if not v:
        return v
    
    phone_obj = PhoneNumber(v)
    if not phone_obj.is_valid:
        raise ValueError(f"Invalid phone number: {v}")
    
    return phone_obj.normalized


class PhoneValidator:
    """
    Pydantic validator class for phone numbers.
    
    Usage:
        from pydantic import BaseModel, validator
        
        class User(BaseModel):
            phone: str
            
            @validator('phone')
            def validate_phone(cls, v):
                return PhoneValidator.validate(v)
    """
    
    @staticmethod
    def validate(v: str) -> str:
        """Validate and normalize phone number."""
        if not v:
            return v
        
        phone_obj = PhoneNumber(v)
        if not phone_obj.is_valid:
            raise ValueError(f"Invalid phone number: {v}")
        
        return phone_obj.normalized
    
    @staticmethod
    def optional(v: Optional[str]) -> Optional[str]:
        """Validate optional phone number."""
        if not v:
            return v
        
        return PhoneValidator.validate(v)


# ─── Phone Number Models ──────────────────────────────────────

from pydantic import BaseModel, Field, field_validator


class PhoneNumberModel(BaseModel):
    """Phone number model with validation."""
    
    phone: str = Field(..., description="Phone number")
    
    @field_validator('phone')
    def validate_phone(cls, v: str) -> str:
        return PhoneValidator.validate(v)


class MpesaPhoneModel(BaseModel):
    """Phone number model for M-Pesa."""
    
    phone: str = Field(..., description="M-Pesa phone number")
    
    @field_validator('phone')
    def validate_mpesa_phone(cls, v: str) -> str:
        phone_obj = PhoneNumber(v)
        if not phone_obj.is_valid:
            raise ValueError(f"Invalid phone number: {v}")
        
        # M-Pesa requires Safaricom or Airtel
        if phone_obj.network not in ['Safaricom', 'Airtel']:
            raise ValueError(f"Phone number must be on Safaricom or Airtel network")
        
        return phone_obj.normalized


# ─── Example Usage ─────────────────────────────────────────────

if __name__ == "__main__":
    # Test phone numbers
    test_numbers = [
        "0712345678",
        "0723456789",
        "+254712345678",
        "254723456789",
        "0733456789",
        "071234567",
        "1234567890"
    ]
    
    for num in test_numbers:
        print(f"\n📱 Testing: {num}")
        phone = PhoneNumber(num)
        print(f"  Valid: {phone.is_valid}")
        if phone.is_valid:
            print(f"  Normalized: {phone.normalized}")
            print(f"  Display: {phone.display}")
            print(f"  Network: {phone.network}")
            print(f"  Safaricom: {phone.is_safaricom}")
        else:
            print(f"  ❌ Invalid phone number")
