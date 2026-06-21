# services/vin_validator.py - Add is_valid_vin function
import re
from typing import Dict, Any, Optional, List

def is_valid_vin(vin: str) -> bool:
    """
    Simple VIN validation (for backward compatibility)
    
    Args:
        vin: VIN to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not vin:
        return False
    
    vin = vin.upper().strip()
    
    # VIN must be 17 characters
    if len(vin) != 17:
        return False
    
    # VIN cannot contain I, O, Q
    if re.search(r"[IOQ]", vin):
        return False
    
    # Must be alphanumeric
    if not vin.isalnum():
        return False
    
    return True

# Keep the existing VINValidator class
class VINValidator:
    """Comprehensive VIN validation service"""
    
    @classmethod
    def validate(cls, vin: str) -> Dict[str, Any]:
        """Validate VIN with detailed results"""
        # ... existing code ...
        pass
    
    @classmethod
    def is_valid(cls, vin: str) -> bool:
        """Quick validation check"""
        return is_valid_vin(vin)

# Create singleton instance
vin_validator = VINValidator()
