# backend/services/vin_validator.py
import re
from typing import Dict, Any, Optional, Tuple

class VINValidator:
    """
    Comprehensive VIN validation service
    Implements full VIN validation including check digit verification
    """
    
    # VIN character weights for check digit calculation
    VIN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
    
    # Character translation values
    VIN_TRANSLATION = {
        'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
        'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
        'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9
    }
    
    # Invalid characters (I, O, Q)
    INVALID_CHARS = ['I', 'O', 'Q']
    
    # Valid VIN characters
    VALID_CHARS = set('ABCDEFGHJKLMNPRSTUVWXYZ0123456789')
    
    @classmethod
    def validate(cls, vin: str) -> Dict[str, Any]:
        """
        Comprehensive VIN validation
        
        Args:
            vin: VIN to validate
            
        Returns:
            Dict with validation results
        """
        if not vin:
            return {
                "valid": False,
                "error": "VIN is empty",
                "vin": None
            }
        
        # Clean and normalize
        vin = cls._clean_vin(vin)
        
        # Run all validation checks
        checks = {
            "length": cls._check_length(vin),
            "characters": cls._check_characters(vin),
            "invalid_chars": cls._check_invalid_chars(vin),
            "check_digit": cls._check_check_digit(vin),
            "structure": cls._check_structure(vin)
        }
        
        # Determine if valid
        is_valid = all(checks.values())
        
        return {
            "valid": is_valid,
            "vin": vin,
            "checks": checks,
            "errors": cls._get_errors(checks),
            "details": {
                "manufacturer": cls._extract_manufacturer(vin) if is_valid else None,
                "model_year": cls._extract_model_year(vin) if is_valid else None,
                "plant": cls._extract_plant(vin) if is_valid else None,
                "serial": cls._extract_serial(vin) if is_valid else None,
                "region": cls._extract_region(vin) if is_valid else None
            }
        }
    
    @classmethod
    def is_valid(cls, vin: str) -> bool:
        """Simple boolean validation"""
        result = cls.validate(vin)
        return result.get("valid", False)
    
    @classmethod
    def _clean_vin(cls, vin: str) -> str:
        """Clean and normalize VIN"""
        # Remove whitespace and special characters
        vin = re.sub(r'[^A-Za-z0-9]', '', vin)
        # Convert to uppercase
        return vin.upper()
    
    @classmethod
    def _check_length(cls, vin: str) -> bool:
        """Check VIN length is exactly 17 characters"""
        return len(vin) == 17
    
    @classmethod
    def _check_characters(cls, vin: str) -> bool:
        """Check VIN contains only valid characters"""
        return all(c in cls.VALID_CHARS for c in vin)
    
    @classmethod
    def _check_invalid_chars(cls, vin: str) -> bool:
        """Check VIN doesn't contain I, O, Q"""
        return not any(c in vin for c in cls.INVALID_CHARS)
    
    @classmethod
    def _check_check_digit(cls, vin: str) -> bool:
        """
        Validate VIN check digit (position 9)
        
        VIN check digit calculation:
        1. Assign values to each character
        2. Multiply by weights
        3. Sum products
        4. Divide by 11
        5. Check digit is remainder (10 = X)
        """
        if len(vin) != 17:
            return False
        
        # Validate all characters are valid for calculation
        for char in vin:
            if char not in cls.VIN_TRANSLATION:
                return False
        
        # Calculate check digit
        total = 0
        for i, char in enumerate(vin):
            value = cls.VIN_TRANSLATION.get(char, 0)
            total += value * cls.VIN_WEIGHTS[i]
        
        remainder = total % 11
        
        # 10 is represented as 'X'
        expected_check = str(remainder) if remainder < 10 else 'X'
        
        # Position 9 (0-indexed) is the check digit
        actual_check = vin[8]
        
        return actual_check == expected_check
    
    @classmethod
    def _check_structure(cls, vin: str) -> bool:
        """
        Check VIN structure:
        - Positions 1-3: Manufacturer (WMI)
        - Position 9: Check digit
        - Position 10: Model year
        - Position 11: Plant
        - Positions 12-17: Serial number
        """
        if len(vin) != 17:
            return False
        
        # Position 1-3 should be alphanumeric
        if not re.match(r'^[A-HJ-NPR-Z0-9]{3}$', vin[:3]):
            return False
        
        # Position 10 should be a valid year code
        year_code = vin[9]
        valid_year_codes = 'ABCDEFGHJKLMNPRSTUVWXYZ1234567890'
        if year_code not in valid_year_codes:
            return False
        
        # Positions 12-17 should be alphanumeric
        if not re.match(r'^[A-HJ-NPR-Z0-9]{6}$', vin[11:]):
            return False
        
        return True
    
    @classmethod
    def _get_errors(cls, checks: Dict[str, bool]) -> list:
        """Get list of validation errors"""
        errors = []
        
        if not checks.get("length"):
            errors.append("VIN must be exactly 17 characters")
        
        if not checks.get("characters"):
            errors.append("VIN contains invalid characters")
        
        if not checks.get("invalid_chars"):
            errors.append("VIN contains invalid characters: I, O, or Q")
        
        if not checks.get("check_digit"):
            errors.append("Invalid check digit")
        
        if not checks.get("structure"):
            errors.append("Invalid VIN structure")
        
        return errors
    
    @classmethod
    def _extract_manufacturer(cls, vin: str) -> str:
        """Extract manufacturer from WMI (positions 1-3)"""
        if len(vin) >= 3:
            return vin[:3]
        return None
    
    @classmethod
    def _extract_model_year(cls, vin: str) -> Optional[int]:
        """Extract model year from position 10"""
        if len(vin) >= 10:
            year_code = vin[9]
            year_map = {
                'A': 1980, 'B': 1981, 'C': 1982, 'D': 1983, 'E': 1984,
                'F': 1985, 'G': 1986, 'H': 1987, 'J': 1988, 'K': 1989,
                'L': 1990, 'M': 1991, 'N': 1992, 'P': 1993, 'R': 1994,
                'S': 1995, 'T': 1996, 'V': 1997, 'W': 1998, 'X': 1999,
                'Y': 2000, '1': 2001, '2': 2002, '3': 2003, '4': 2004,
                '5': 2005, '6': 2006, '7': 2007, '8': 2008, '9': 2009,
                'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014,
                'F': 2015, 'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019,
                'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024,
                'S': 2025, 'T': 2026, 'V': 2027, 'W': 2028, 'X': 2029,
                'Y': 2030
            }
            
            # Handle 2010+ (A = 2010, B = 2011, etc.)
            if year_code in year_map:
                return year_map[year_code]
        
        return None
    
    @classmethod
    def _extract_plant(cls, vin: str) -> str:
        """Extract plant code from position 11"""
        if len(vin) >= 11:
            return vin[10]
        return None
    
    @classmethod
    def _extract_serial(cls, vin: str) -> str:
        """Extract serial number from positions 12-17"""
        if len(vin) >= 17:
            return vin[11:]
        return None
    
    @classmethod
    def _extract_region(cls, vin: str) -> str:
        """Extract region from first character"""
        if len(vin) >= 1:
            first_char = vin[0]
            region_map = {
                '1': 'USA', '2': 'Canada', '3': 'Mexico',
                '4': 'USA', '5': 'USA',
                'J': 'Japan', 'K': 'Korea',
                'S': 'United Kingdom',
                'W': 'Germany',
                'Y': 'Sweden',
                'Z': 'Italy'
            }
            return region_map.get(first_char, 'Unknown')
        return None
    
    @classmethod
    def generate_check_digit(cls, vin_without_check: str) -> str:
        """
        Generate check digit for a VIN without it
        
        Args:
            vin_without_check: First 8 characters + positions 10-17 (16 chars total)
            
        Returns:
            Check digit (0-9 or X)
        """
        if len(vin_without_check) != 16:
            raise ValueError("VIN without check digit must be 16 characters")
        
        # Insert placeholder for check digit at position 9
        vin_full = vin_without_check[:8] + '0' + vin_without_check[8:]
        
        total = 0
        for i, char in enumerate(vin_full):
            value = cls.VIN_TRANSLATION.get(char, 0)
            total += value * cls.VIN_WEIGHTS[i]
        
        remainder = total % 11
        return str(remainder) if remainder < 10 else 'X'
    
    @classmethod
    def suggest_corrections(cls, vin: str) -> list:
        """
        Suggest possible corrections for invalid VIN
        
        Args:
            vin: Invalid VIN
            
        Returns:
            List of suggested corrections
        """
        suggestions = []
        vin = cls._clean_vin(vin)
        
        # Check for common typos
        corrections = {
            'I': '1',  # I mistaken for 1
            'O': '0',  # O mistaken for 0
            'Q': '0',  # Q mistaken for 0
            'S': '5',  # S mistaken for 5
            'B': '8',  # B mistaken for 8
        }
        
        # Try each correction
        for old, new in corrections.items():
            if old in vin:
                corrected = vin.replace(old, new)
                if cls.is_valid(corrected):
                    suggestions.append({
                        "original": vin,
                        "corrected": corrected,
                        "change": f"Replaced '{old}' with '{new}'"
                    })
        
        # Try check digit correction
        if len(vin) == 17:
            try:
                # Extract positions without check digit
                vin_without_check = vin[:8] + vin[9:]
                new_check = cls.generate_check_digit(vin_without_check)
                if new_check != vin[8]:
                    corrected = vin[:8] + new_check + vin[9:]
                    suggestions.append({
                        "original": vin,
                        "corrected": corrected,
                        "change": f"Corrected check digit from '{vin[8]}' to '{new_check}'"
                    })
            except:
                pass
        
        return suggestions

# Initialize validator
vin_validator = VINValidator()
