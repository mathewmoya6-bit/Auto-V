# services/vin_validation_service.py
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from services.supabase_client import get_supabase
from services.vin_validator import vin_validator
from services.carapi_service import car_api

logger = logging.getLogger(__name__)

class VINValidationService:
    """
    Comprehensive VIN validation and fraud detection service
    """
    
    def __init__(self):
        self.supabase = get_supabase()
        
        # Fraud detection thresholds
        self.FRAUD_THRESHOLDS = {
            "HIGH": {"min_score": 0.7, "action": "block"},
            "MEDIUM": {"min_score": 0.4, "action": "review"},
            "LOW": {"min_score": 0.0, "action": "allow"}
        }
        
        # Suspicious patterns
        self.SUSPICIOUS_PATTERNS = {
            "repeated_chars": r'(.)\1{4,}',  # 5+ repeated characters
            "sequential": r'(0123456789|9876543210|abcdefghijklmnopqrstuvwxyz)',
            "common_fake": r'(123456789|111111111|000000000|TEST|FAKE|DEMO)'
        }
        
        # Known fraud indicators
        self.FRAUD_INDICATORS = {
            "rapid_scans": {"threshold": 10, "window_minutes": 5},
            "multiple_vehicles": {"threshold": 5, "window_minutes": 10},
            "invalid_patterns": {"threshold": 3, "window_minutes": 5}
        }

    # ─── MAIN VALIDATION ──────────────────────────────────────

    def validate_vin_against_db(self, vin: str) -> Dict[str, Any]:
        """
        Validate VIN against database with fraud detection
        
        Args:
            vin: Vehicle Identification Number
            
        Returns:
            Dict with validation results and risk assessment
        """
        try:
            # Clean VIN
            vin = self._clean_vin(vin)
            
            # 1. Basic validation
            basic_validation = vin_validator.validate(vin)
            
            if not basic_validation.get("valid"):
                return {
                    "match": False,
                    "risk": "HIGH",
                    "reason": "Invalid VIN format",
                    "validation": basic_validation,
                    "errors": basic_validation.get("errors", [])
                }
            
            # 2. Check against database
            vehicle = self._get_vehicle_from_db(vin)
            
            if not vehicle:
                return {
                    "match": False,
                    "risk": "HIGH",
                    "reason": "VIN not found in system",
                    "validation": basic_validation,
                    "suggestions": self._suggest_alternatives(vin)
                }
            
            # 3. Fraud detection
            fraud_check = self._check_fraud_indicators(vin, vehicle)
            
            # 4. Comprehensive validation
            result = {
                "match": True,
                "risk": fraud_check.get("risk_level", "LOW"),
                "risk_score": fraud_check.get("risk_score", 0.0),
                "vehicle": vehicle,
                "validation": basic_validation,
                "fraud_indicators": fraud_check.get("indicators", []),
                "fraud_flags": fraud_check.get("flags", []),
                "recommendation": fraud_check.get("recommendation", "allow"),
                "timestamp": datetime.now().isoformat()
            }
            
            # 5. Log validation
            self._log_validation(vin, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                "match": False,
                "risk": "HIGH",
                "reason": f"Validation error: {str(e)}",
                "error": str(e)
            }

    # ─── COMPREHENSIVE FRAUD CHECK ────────────────────────────

    def comprehensive_fraud_check(self, vin: str, user_id: str = None, ip_address: str = None) -> Dict[str, Any]:
        """
        Comprehensive fraud detection for VIN validation
        
        Args:
            vin: Vehicle Identification Number
            user_id: Optional user ID for behavior analysis
            ip_address: Optional IP address for geo-analysis
            
        Returns:
            Dict with fraud analysis results
        """
        try:
            vin = self._clean_vin(vin)
            
            # Initialize results
            fraud_score = 0.0
            indicators = []
            flags = []
            
            # 1. Check VIN pattern
            pattern_check = self._check_vin_pattern(vin)
            if pattern_check.get("suspicious"):
                fraud_score += 0.3
                indicators.append(pattern_check)
                flags.append("suspicious_vin_pattern")
            
            # 2. Check against database
            vehicle = self._get_vehicle_from_db(vin)
            if not vehicle:
                fraud_score += 0.2
                indicators.append({"type": "not_found", "message": "VIN not in database"})
                flags.append("vin_not_found")
            else:
                # 3. Check vehicle consistency
                consistency_check = self._check_vehicle_consistency(vin, vehicle)
                if consistency_check.get("issues"):
                    fraud_score += 0.2
                    indicators.append(consistency_check)
                    flags.append("inconsistent_vehicle_data")
            
            # 4. Check user behavior (if user_id provided)
            if user_id:
                behavior_check = self._check_user_behavior(user_id, vin)
                if behavior_check.get("suspicious"):
                    fraud_score += 0.25
                    indicators.append(behavior_check)
                    flags.append("suspicious_user_behavior")
            
            # 5. Check IP geo-location (if IP provided)
            if ip_address:
                geo_check = self._check_geo_location(ip_address, vin)
                if geo_check.get("suspicious"):
                    fraud_score += 0.1
                    indicators.append(geo_check)
                    flags.append("suspicious_geo_location")
            
            # 6. Determine risk level
            risk_level = self._determine_risk_level(fraud_score)
            
            return {
                "risk_score": round(fraud_score, 2),
                "risk_level": risk_level,
                "indicators": indicators,
                "flags": flags,
                "recommendation": self._get_recommendation(risk_level),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Fraud check error: {str(e)}")
            return {
                "risk_score": 0.5,
                "risk_level": "MEDIUM",
                "indicators": [{"type": "error", "message": str(e)}],
                "flags": ["check_error"],
                "recommendation": "review"
            }

    # ─── INDIVIDUAL CHECKS ─────────────────────────────────────

    def _get_vehicle_from_db(self, vin: str) -> Optional[Dict[str, Any]]:
        """Get vehicle from database"""
        try:
            result = self.supabase.get_vehicle_by_vin(vin)
            return result[0] if result else None
        except Exception as e:
            logger.error(f"DB query error: {str(e)}")
            return None

    def _check_vin_pattern(self, vin: str) -> Dict[str, Any]:
        """Check for suspicious VIN patterns"""
        suspicious = False
        reasons = []
        
        # Check for repeated characters
        if re.search(self.SUSPICIOUS_PATTERNS["repeated_chars"], vin):
            suspicious = True
            reasons.append("Repeated characters detected")
        
        # Check for sequential patterns
        if re.search(self.SUSPICIOUS_PATTERNS["sequential"], vin.lower()):
            suspicious = True
            reasons.append("Sequential pattern detected")
        
        # Check for common fake VINs
        if re.search(self.SUSPICIOUS_PATTERNS["common_fake"], vin):
            suspicious = True
            reasons.append("Common fake VIN pattern detected")
        
        return {
            "type": "vin_pattern",
            "suspicious": suspicious,
            "reasons": reasons,
            "vin": vin
        }

    def _check_vehicle_consistency(self, vin: str, vehicle: Dict[str, Any]) -> Dict[str, Any]:
        """Check vehicle data consistency"""
        issues = []
        
        # Check if vehicle has all required fields
        required_fields = ['make', 'model', 'year', 'vin']
        for field in required_fields:
            if not vehicle.get(field):
                issues.append(f"Missing required field: {field}")
        
        # Check year validity
        year = vehicle.get('year')
        if year:
            current_year = datetime.now().year
            if year < 1900 or year > current_year + 1:
                issues.append(f"Invalid year: {year}")
        
        # Check for suspicious modifications
        if vehicle.get('modified_date'):
            modified_date = datetime.fromisoformat(vehicle['modified_date'])
            if (datetime.now() - modified_date).days > 365:
                issues.append("Vehicle record older than 1 year")
        
        return {
            "type": "vehicle_consistency",
            "has_issues": len(issues) > 0,
            "issues": issues,
            "vehicle": vehicle
        }

    def _check_user_behavior(self, user_id: str, vin: str) -> Dict[str, Any]:
        """Check user behavior for suspicious patterns"""
        suspicious = False
        reasons = []
        
        try:
            # Get user's scan history
            scans = self.supabase.get_vin_scans(user_id, limit=50)
            
            if scans:
                # Check for rapid scans
                recent_scans = [s for s in scans if s.get('scanned_at')]
                if recent_scans:
                    last_scan_time = datetime.fromisoformat(recent_scans[0]['scanned_at'])
                    if (datetime.now() - last_scan_time).seconds < 60:
                        suspicious = True
                        reasons.append("Rapid consecutive scans detected")
                
                # Check for duplicate VIN scans
                duplicate_scans = [s for s in scans if s.get('vin') == vin]
                if len(duplicate_scans) > 5:
                    suspicious = True
                    reasons.append(f"Multiple scans of same VIN ({len(duplicate_scans)})")
                
                # Check for multiple different VINs in short time
                unique_vins = set(s.get('vin') for s in scans if s.get('vin'))
                if len(unique_vins) > 20:
                    suspicious = True
                    reasons.append(f"Large number of unique VINs scanned ({len(unique_vins)})")
            
        except Exception as e:
            logger.error(f"User behavior check error: {str(e)}")
        
        return {
            "type": "user_behavior",
            "suspicious": suspicious,
            "reasons": reasons,
            "user_id": user_id
        }

    def _check_geo_location(self, ip_address: str, vin: str) -> Dict[str, Any]:
        """Check geo-location for suspicious activity"""
        suspicious = False
        reasons = []
        
        try:
            # Basic IP validation
            if not ip_address or ip_address == '127.0.0.1':
                suspicious = True
                reasons.append("Local or unknown IP address")
            
            # Check for VPN/proxy patterns (simplified)
            vpn_patterns = ['vpn', 'proxy', 'tor', 'cloud']
            if any(pattern in ip_address.lower() for pattern in vpn_patterns):
                suspicious = True
                reasons.append("VPN or proxy detected")
            
        except Exception as e:
            logger.error(f"Geo-location check error: {str(e)}")
        
        return {
            "type": "geo_location",
            "suspicious": suspicious,
            "reasons": reasons,
            "ip_address": ip_address
        }

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on score"""
        if score >= 0.7:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"

    def _get_recommendation(self, risk_level: str) -> str:
        """Get recommendation based on risk level"""
        recommendations = {
            "HIGH": "block",
            "MEDIUM": "review",
            "LOW": "allow"
        }
        return recommendations.get(risk_level, "review")

    # ─── UTILITY FUNCTIONS ─────────────────────────────────────

    def _clean_vin(self, vin: str) -> str:
        """Clean and normalize VIN"""
        if not vin:
            return ""
        vin = re.sub(r'[^A-Za-z0-9]', '', vin)
        return vin.upper()

    def _suggest_alternatives(self, vin: str) -> List[str]:
        """Suggest possible valid VIN alternatives"""
        suggestions = []
        
        # Check for common typos
        corrections = {
            'I': '1', 'O': '0', 'Q': '0',
            'S': '5', 'B': '8', 'G': '6'
        }
        
        for old, new in corrections.items():
            if old in vin:
                corrected = vin.replace(old, new)
                if vin_validator.is_valid(corrected):
                    suggestions.append(corrected)
        
        return suggestions

    def _log_validation(self, vin: str, result: Dict[str, Any]):
        """Log validation result for audit"""
        try:
            log_entry = {
                "vin": vin,
                "risk_level": result.get("risk", "UNKNOWN"),
                "risk_score": result.get("risk_score", 0.0),
                "match": result.get("match", False),
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in database or log file
            logger.info(f"VIN Validation: {log_entry}")
            
        except Exception as e:
            logger.error(f"Log validation error: {str(e)}")

    # ─── BATCH VALIDATION ─────────────────────────────────────

    def batch_validate(self, vins: List[str]) -> List[Dict[str, Any]]:
        """Validate multiple VINs in batch"""
        results = []
        
        for vin in vins:
            try:
                result = self.validate_vin_against_db(vin)
                results.append(result)
            except Exception as e:
                results.append({
                    "vin": vin,
                    "match": False,
                    "risk": "HIGH",
                    "reason": f"Validation error: {str(e)}"
                })
        
        return results

    # ─── STATISTICS ────────────────────────────────────────────

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        try:
            # Get recent validations from logs
            # This would typically query a database table
            
            return {
                "total_validations": 0,
                "high_risk": 0,
                "medium_risk": 0,
                "low_risk": 0,
                "matches": 0,
                "non_matches": 0,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Stats error: {str(e)}")
            return {"error": str(e)}

# ─── SINGLETON INSTANCE ──────────────────────────────────────

_validation_service = None

def get_validation_service() -> VINValidationService:
    """Get validation service instance"""
    global _validation_service
    if _validation_service is None:
        _validation_service = VINValidationService()
    return _validation_service

# ─── CONVENIENCE FUNCTIONS ────────────────────────────────────

def validate_vin_against_db(vin: str) -> Dict[str, Any]:
    """Convenience function for basic validation"""
    service = get_validation_service()
    return service.validate_vin_against_db(vin)

def comprehensive_fraud_check(vin: str, user_id: str = None, ip_address: str = None) -> Dict[str, Any]:
    """Convenience function for comprehensive fraud check"""
    service = get_validation_service()
    return service.comprehensive_fraud_check(vin, user_id, ip_address)

# ─── QUICK TEST ──────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing VIN Validation Service...")
    
    # Test VINs
    test_vins = [
        "JTEGD34V000123456",  # Valid
        "JTEGD34V0001I3456",  # Invalid (contains I)
        "12345678901234567",  # Fake
    ]
    
    service = get_validation_service()
    
    for vin in test_vins:
        print(f"\nTesting VIN: {vin}")
        result = service.validate_vin_against_db(vin)
        
        print(f"Match: {result.get('match')}")
        print(f"Risk: {result.get('risk')}")
        print(f"Reason: {result.get('reason', 'N/A')}")
        
        # Fraud check
        fraud = service.comprehensive_fraud_check(vin)
        print(f"Fraud Score: {fraud.get('risk_score')}")
        print(f"Fraud Level: {fraud.get('risk_level')}")
        print(f"Flags: {fraud.get('flags', [])}")
