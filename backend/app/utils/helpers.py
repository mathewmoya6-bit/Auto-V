import re
from datetime import datetime, date
from typing import Optional, Dict, Any
import uuid


def validate_phone_number(phone: str) -> bool:
    """Validate Kenyan phone number format"""
    # Remove any whitespace
    phone = phone.strip()
    
    # Check format: 0712345678, +254712345678, 254712345678
    pattern = r'^(?:\+254|0|254)?[7]\d{8}$'
    return bool(re.match(pattern, phone))


def format_phone_number(phone: str) -> str:
    """Format phone number to international format"""
    phone = phone.strip()
    
    # Remove any non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # Remove leading 0 if present
    if phone.startswith('0'):
        phone = phone[1:]
    
    # Add country code if missing
    if not phone.startswith('254'):
        phone = '254' + phone
    
    # Return with + prefix
    return f"+{phone}"


def generate_vehicle_id() -> str:
    """Generate a unique vehicle ID"""
    return f"VHC{uuid.uuid4().hex[:8].upper()}"


def calculate_age(birth_date: date) -> int:
    """Calculate age from birth date"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def parse_date(date_str: str) -> Optional[date]:
    """Parse date string to date object"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def format_currency(amount: float, currency: str = "KES") -> str:
    """Format amount as currency"""
    return f"{currency} {amount:,.2f}"


def calculate_vehicle_age(year: int) -> int:
    """Calculate vehicle age from year"""
    current_year = datetime.now().year
    return current_year - year


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values from dictionary"""
    return {k: v for k, v in data.items() if v is not None}


def generate_reference_number(prefix: str = "REF") -> str:
    """Generate a unique reference number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = uuid.uuid4().hex[:6].upper()
    return f"{prefix}{timestamp}{random_str}"


def truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate string to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def extract_domain(email: str) -> str:
    """Extract domain from email"""
    try:
        return email.split('@')[1]
    except IndexError:
        return ""
