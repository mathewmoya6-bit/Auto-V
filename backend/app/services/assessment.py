# ============================================================
# AUTO-V ASSESSMENT ENGINE - COMPLETE PRODUCTION MODULE
# assessment/assessment_engine.py
# ============================================================

"""
AUTO-V Assessment Engine - Africa's Vehicle Intelligence Platform
All assessment modules combined into a single production file.
"""

import hashlib
import json
import math
import random
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

# ============================================================
# CONSTANTS & CONFIGURATION
# ============================================================

class AssessmentType(str, Enum):
    ACCIDENT = "accident"
    INSURANCE_CLAIM = "insurance_claim"
    REPAIR_COST = "repair_cost"
    TOTAL_LOSS = "total_loss"
    SALVAGE = "salvage"
    THEFT_RECOVERY = "theft_recovery"

class DamageSeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    SEVERE = "severe"
    CATASTROPHIC = "catastrophic"

class ConditionGrade(str, Enum):
    A = "A"  # Excellent
    B = "B"  # Good
    C = "C"  # Fair
    D = "D"  # Poor
    E = "E"  # Salvage

ASSESSMENT_PRICES = {
    AssessmentType.ACCIDENT.value: 3500,
    AssessmentType.INSURANCE_CLAIM.value: 4000,
    AssessmentType.REPAIR_COST.value: 3000,
    AssessmentType.TOTAL_LOSS.value: 4000,
    AssessmentType.SALVAGE.value: 3500,
    AssessmentType.THEFT_RECOVERY.value: 4000,
}

# Vehicle segments
VEHICLE_SEGMENTS = {
    "small": {"base_cost": 150000, "labour_rate": 2000},
    "compact": {"base_cost": 200000, "labour_rate": 2200},
    "midsize": {"base_cost": 280000, "labour_rate": 2500},
    "large": {"base_cost": 400000, "labour_rate": 2800},
    "suv": {"base_cost": 350000, "labour_rate": 2600},
    "pickup": {"base_cost": 300000, "labour_rate": 2500},
    "van": {"base_cost": 320000, "labour_rate": 2400},
    "luxury": {"base_cost": 600000, "labour_rate": 3500},
}

SEVERITY_MULTIPLIERS = {
    DamageSeverity.MINOR.value: 0.3,
    DamageSeverity.MODERATE.value: 0.6,
    DamageSeverity.MAJOR.value: 0.9,
    DamageSeverity.SEVERE.value: 1.2,
    DamageSeverity.CATASTROPHIC.value: 1.5,
}

PARTS_FACTOR = {
    "engine": 0.40, "transmission": 0.30, "suspension": 0.15,
    "brakes": 0.10, "body": 0.25, "paint": 0.08,
    "electrical": 0.12, "interior": 0.10, "chassis": 0.35,
    "tyres": 0.05, "airbags": 0.20, "cooling": 0.10,
    "exhaust": 0.08, "fuel_system": 0.15, "steering": 0.18,
}

SALVAGE_PERCENTAGE = {
    DamageSeverity.MINOR.value: 0.85,
    DamageSeverity.MODERATE.value: 0.65,
    DamageSeverity.MAJOR.value: 0.45,
    DamageSeverity.SEVERE.value: 0.25,
    DamageSeverity.CATASTROPHIC.value: 0.10,
}

THEFT_RECOVERY_FACTORS = {
    "excellent": 0.95, "good": 0.85, "fair": 0.70,
    "poor": 0.50, "damaged": 0.30,
}

TOTAL_LOSS_THRESHOLD = 0.65

# ============================================================
# DATA CLASSES & SCHEMAS
# ============================================================

@dataclass
class Vehicle:
    make: str
    model: str
    year: int
    reg_number: str = ""
    vin: str = ""
    odometer: int = 0
    market_value: int = 0
    body_type: str = ""
    fuel_type: str = ""
    transmission: str = ""
    engine_capacity: int = 0
    colour: str = ""
    
    def get_segment(self) -> str:
        """Determine vehicle segment based on make/model."""
        make_lower = self.make.lower()
        model_lower = self.model.lower()
        
        luxury_brands = ["mercedes", "bmw", "audi", "lexus", "jaguar", "land rover", "porsche", "volvo"]
        if any(b in make_lower for b in luxury_brands):
            return "luxury"
        
        suv_models = ["rav4", "cr-v", "x-trail", "forester", "outlander", "tucson", "sportage", "cx-5", "fortuner", "prado"]
        if any(m in model_lower for m in suv_models) or "suv" in model_lower:
            return "suv"
        
        pickup_models = ["hilux", "ranger", "d-max", "navara", "triton"]
        if any(m in model_lower for m in pickup_models):
            return "pickup"
        
        van_models = ["hiace", "transit", "delica", "nv200", "voxy", "noah"]
        if any(m in model_lower for m in van_models):
            return "van"
        
        large_models = ["camry", "accord", "legacy", "mazda6", "passat", "superb", "crown"]
        if any(m in model_lower for m in large_models):
            return "large"
        
        midsize_models = ["corolla", "civic", "axio", "premio", "allion", "elantra", "cerato", "3", "c-class"]
        if any(m in model_lower for m in midsize_models):
            return "midsize"
        
        compact_models = ["vitz", "fit", "note", "swift", "rio", "i20", "polo", "208", "yaris", "jazz"]
        if any(m in model_lower for m in compact_models):
            return "compact"
        
        return "compact"

@dataclass
class Inspector:
    name: str
    credentials: str = ""
    reg_number: str = ""
    company: str = ""
    signature: str = ""
    
@dataclass
class DamageMark:
    panel: str
    damage_type: str
    severity: str
    notes: str = ""

@dataclass
class AssessmentResult:
    assessment_id: str
    type: str
    vehicle: Dict[str, Any]
    inspector: Dict[str, Any]
    generated_at: str
    status: str = "completed"
    confidence_score: int = 85
    
    # Assessment-specific fields
    repair_estimate: Optional[Dict[str, Any]] = None
    total_loss: Optional[bool] = None
    salvage_value: Optional[int] = None
    estimated_payout: Optional[int] = None
    recommendation: Optional[str] = None
    claim_valid: Optional[bool] = None
    loss_ratio: Optional[float] = None
    damage_score: Optional[float] = None
    condition_grade: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

# ============================================================
# WORKFLOW ENGINE
# ============================================================

class WorkflowEngine:
    """Controls the entire assessment workflow lifecycle."""
    
    def __init__(self):
        self.workflow_states = [
            "created", "vehicle_loaded", "inspection_started", 
            "images_uploaded", "ai_analyzed", "inspector_reviewed",
            "report_generated", "digitally_signed", "archived"
        ]
    
    def generate_assessment_id(self, prefix: str = "ASS") -> str:
        """Generate a unique assessment ID."""
        timestamp = datetime.now().strftime("%Y%m%d")
        random_suffix = f"{random.randint(1000, 9999)}"
        return f"{prefix}-{timestamp}-{random_suffix}"
    
    def get_next_state(self, current_state: str) -> Optional[str]:
        """Get the next state in the workflow."""
        if current_state not in self.workflow_states:
            return None
        index = self.workflow_states.index(current_state)
        if index < len(self.workflow_states) - 1:
            return self.workflow_states[index + 1]
        return None
    
    def is_complete(self, state: str) -> bool:
        """Check if assessment is complete."""
        return state == "archived"
    
    def can_proceed(self, state: str) -> bool:
        """Check if assessment can proceed to next state."""
        return state not in ["archived", "report_generated", "digitally_signed"]

# ============================================================
# VEHICLE IDENTIFICATION ENGINE
# ============================================================

class VehicleIdentificationEngine:
    """Validates and enriches vehicle information."""
    
    def validate_registration(self, reg: str) -> bool:
        """Validate Kenyan registration number format."""
        patterns = [
            r'^[A-Z]{3}\s?\d{3}[A-Z]?$',  # KCA 123A
            r'^[A-Z]{2}\s?\d{4}[A-Z]?$',   # KC 1234A
            r'^[A-Z]{3}\s?\d{4}$',          # KCA 1234
        ]
        return any(re.match(p, reg.strip().upper()) for p in patterns)
    
    def validate_vin(self, vin: str) -> bool:
        """Validate VIN format (17 characters)."""
        vin = vin.strip().upper()
        if len(vin) != 17:
            return False
        # Exclude I, O, Q
        if any(c in vin for c in ['I', 'O', 'Q']):
            return False
        return bool(re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin))
    
    def decode_vin(self, vin: str) -> Dict[str, Any]:
        """Decode VIN to retrieve vehicle information."""
        if not self.validate_vin(vin):
            return {"error": "Invalid VIN format"}
        
        # Mock VIN decoding - in production, use a real VIN API
        # This is just a placeholder for the engine
        return {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "body_type": "Sedan",
            "fuel_type": "Petrol",
            "engine_capacity": 1800,
            "country": "Japan",
        }
    
    def enrich_vehicle(self, vehicle: Vehicle) -> Vehicle:
        """Enrich vehicle with additional data."""
        # Add depreciation rate based on age
        current_year = datetime.now().year
        age = current_year - vehicle.year
        vehicle.depreciation_rate = min(0.85, age * 0.05)
        return vehicle

# ============================================================
# INSPECTION VALIDATION ENGINE
# ============================================================

class InspectionValidationEngine:
    """Validates that inspection is complete and meets requirements."""
    
    REQUIRED_IMAGES = [
        "front", "rear", "left", "right",
        "front_left", "front_right", "rear_left", "rear_right",
        "dashboard", "steering_wheel", "seats", "roof", "boot", "odometer",
        "engine_bay", "chassis_number", "vin_plate"
    ]
    
    def validate_completeness(self, images: List[str], checklist: List[Dict]) -> Tuple[bool, List[str]]:
        """Check if inspection is complete."""
        missing = []
        
        # Check images
        for required in self.REQUIRED_IMAGES:
            if not any(required in img.lower() for img in images):
                missing.append(f"Missing image: {required}")
        
        # Check checklist
        for item in checklist:
            if not item.get("checked", False):
                missing.append(f"Checklist item not completed: {item.get('item', 'Unknown')}")
        
        return len(missing) == 0, missing
    
    def get_required_images(self) -> List[str]:
        """Get list of required images."""
        return self.REQUIRED_IMAGES.copy()

# ============================================================
# DAMAGE ANALYSIS ENGINE
# ============================================================

class DamageAnalysisEngine:
    """Analyzes damage data and determines severity."""
    
    def __init__(self):
        self.damage_types = [
            "dent", "scratch", "crack", "missing", "bent", 
            "rust", "fire", "flood", "collision", "corrosion"
        ]
    
    def analyze_damage(self, damage_marks: List[DamageMark]) -> Dict[str, Any]:
        """Analyze damage marks and provide summary."""
        if not damage_marks:
            return {"severity": "none", "parts_affected": [], "score": 0}
        
        # Count damage by severity
        severity_counts = {}
        parts_affected = []
        for mark in damage_marks:
            severity_counts[mark.severity] = severity_counts.get(mark.severity, 0) + 1
            parts_affected.append(mark.panel)
        
        # Determine overall severity
        if DamageSeverity.CATASTROPHIC.value in severity_counts:
            overall = DamageSeverity.CATASTROPHIC.value
        elif DamageSeverity.SEVERE.value in severity_counts:
            overall = DamageSeverity.SEVERE.value
        elif DamageSeverity.MAJOR.value in severity_counts:
            overall = DamageSeverity.MAJOR.value
        elif DamageSeverity.MODERATE.value in severity_counts:
            overall = DamageSeverity.MODERATE.value
        else:
            overall = DamageSeverity.MINOR.value
        
        # Calculate damage score (0-100)
        weights = {DamageSeverity.MINOR.value: 1, DamageSeverity.MODERATE.value: 2,
                   DamageSeverity.MAJOR.value: 3, DamageSeverity.SEVERE.value: 4,
                   DamageSeverity.CATASTROPHIC.value: 5}
        total_weight = sum(weights.get(sev, 1) * count for sev, count in severity_counts.items())
        max_weight = len(damage_marks) * 5
        score = min(100, (total_weight / max_weight) * 100)
        
        return {
            "severity": overall,
            "parts_affected": list(set(parts_affected)),
            "damage_count": len(damage_marks),
            "severity_counts": severity_counts,
            "score": round(score, 1),
            "recommendation": "Immediate repair recommended" if score > 50 else "Minor repair needed"
        }
    
    def get_damage_types(self) -> List[str]:
        return self.damage_types.copy()

# ============================================================
# AI IMAGE RECOGNITION ENGINE
# ============================================================

class AIDamageEngine:
    """AI-powered damage detection from images."""
    
    def __init__(self):
        self.ai_confidence_threshold = 0.7
        self.damage_categories = ["dent", "rust", "missing_parts", "broken_lights", 
                                   "broken_glass", "paint_damage", "flood_damage", 
                                   "fire_damage", "structural_damage"]
    
    def analyze_image(self, image_url: str) -> Dict[str, Any]:
        """
        Analyze a single image for damage.
        This is a mock implementation. In production, call the AI service.
        """
        # Mock AI response - in production, this would call a real AI model
        mock_detections = [
            {"type": "dent", "confidence": random.uniform(0.6, 0.95), "location": "body"},
            {"type": "scratch", "confidence": random.uniform(0.5, 0.9), "location": "paint"},
        ]
        
        # Filter low confidence detections
        detections = [d for d in mock_detections if d["confidence"] >= self.ai_confidence_threshold]
        
        return {
            "detections": detections,
            "summary": f"Found {len(detections)} potential damage areas",
            "confidence": random.uniform(70, 95) if detections else 0,
            "review_required": len(detections) == 0,
        }
    
    def analyze_batch(self, image_urls: List[str]) -> List[Dict[str, Any]]:
        """Analyze multiple images."""
        results = []
        for url in image_urls:
            results.append(self.analyze_image(url))
        return results

# ============================================================
# REPAIR COST ENGINE
# ============================================================

class RepairCostEngine:
    """Calculates comprehensive repair costs."""
    
    def __init__(self):
        self.labour_rate = 2500  # KES per hour
        self.vat_rate = 0.16
    
    def calculate_parts_cost(self, parts_affected: List[str], vehicle: Vehicle, severity: str) -> float:
        """Calculate parts cost based on affected parts."""
        if not parts_affected:
            return 0
        
        segment_data = VEHICLE_SEGMENTS.get(vehicle.get_segment(), VEHICLE_SEGMENTS["compact"])
        base_cost = segment_data["base_cost"]
        severity_mult = SEVERITY_MULTIPLIERS.get(severity, 0.5)
        
        total = 0
        for part in parts_affected:
            factor = PARTS_FACTOR.get(part, 0.10)
            total += base_cost * factor * severity_mult
        
        return math.ceil(total / 100) * 100
    
    def calculate_labour_cost(self, hours: float, vehicle: Vehicle) -> float:
        """Calculate labour cost."""
        segment_data = VEHICLE_SEGMENTS.get(vehicle.get_segment(), VEHICLE_SEGMENTS["compact"])
        rate = segment_data.get("labour_rate", self.labour_rate)
        return math.ceil((hours * rate) / 100) * 100
    
    def calculate_paint_cost(self, parts_affected: List[str], vehicle: Vehicle) -> float:
        """Calculate paint and refinishing cost."""
        # Estimate paint cost based on affected panels
        panel_count = len(parts_affected)
        if panel_count == 0:
            return 0
        
        # Base paint cost per panel
        base_paint_cost = 15000
        total = panel_count * base_paint_cost
        
        # Adjust for vehicle segment
        segment = vehicle.get_segment()
        if segment == "luxury":
            total *= 1.5
        elif segment == "large" or segment == "suv":
            total *= 1.2
        
        return math.ceil(total / 100) * 100
    
    def estimate_repair_cost(self, vehicle: Vehicle, severity: str, parts_affected: List[str], 
                             labour_hours: Optional[float] = None) -> Dict[str, Any]:
        """Generate complete repair estimate."""
        # Calculate components
        parts_cost = self.calculate_parts_cost(parts_affected, vehicle, severity)
        
        # Estimate labour hours if not provided
        if labour_hours is None:
            labour_hours = 4 + (len(parts_affected) * 2)
            if severity in [DamageSeverity.SEVERE.value, DamageSeverity.CATASTROPHIC.value]:
                labour_hours *= 1.5
        
        labour_cost = self.calculate_labour_cost(labour_hours, vehicle)
        paint_cost = self.calculate_paint_cost(parts_affected, vehicle)
        
        # Add VAT
        subtotal = parts_cost + labour_cost + paint_cost
        vat = subtotal * self.vat_rate
        
        total = subtotal + vat
        
        return {
            "parts_cost": parts_cost,
            "labour_cost": labour_cost,
            "paint_cost": paint_cost,
            "labour_hours": labour_hours,
            "subtotal": math.ceil(subtotal / 100) * 100,
            "vat": math.ceil(vat / 100) * 100,
            "total_cost": math.ceil(total / 100) * 100,
            "breakdown": {
                "parts": parts_cost,
                "labour": labour_cost,
                "paint": paint_cost,
                "vat": math.ceil(vat / 100) * 100,
            }
        }

# ============================================================
# MARKET VALUATION ENGINE
# ============================================================

class ValuationEngine:
    """Calculates accurate market valuation."""
    
    def __init__(self):
        self.base_rates = {
            "small": 800000, "compact": 1200000, "midsize": 1800000,
            "large": 2500000, "suv": 2200000, "pickup": 2000000,
            "van": 2100000, "luxury": 4000000,
        }
    
    def calculate_market_value(self, vehicle: Vehicle, condition_score: float = 80) -> int:
        """Calculate market value based on vehicle and condition."""
        segment = vehicle.get_segment()
        base = self.base_rates.get(segment, 1500000)
        
        # Year adjustment (depreciation ~15% per year)
        current_year = datetime.now().year
        age = current_year - vehicle.year
        depreciation = age * 0.10  # 10% per year
        adjusted = base * (1 - depreciation)
        
        # Condition adjustment (0-100 scale, 100 is perfect)
        condition_factor = 0.5 + (condition_score / 200)  # 0.5 to 1.0
        adjusted *= condition_factor
        
        # Odometer adjustment (reduce for high mileage)
        if vehicle.odometer > 100000:
            odometer_reduction = min(0.3, (vehicle.odometer - 100000) / 500000)
            adjusted *= (1 - odometer_reduction)
        
        # Round to nearest 1000
        return math.ceil(adjusted / 1000) * 1000
    
    def get_depreciation_rate(self, vehicle: Vehicle) -> float:
        """Calculate current depreciation rate."""
        current_year = datetime.now().year
        age = current_year - vehicle.year
        return min(0.85, age * 0.10)

# ============================================================
# CONDITION SCORING ENGINE
# ============================================================

class ConditionScoringEngine:
    """Evaluates vehicle condition across multiple categories."""
    
    def __init__(self):
        self.categories = {
            "exterior": {"weight": 0.25, "score": 0},
            "interior": {"weight": 0.20, "score": 0},
            "mechanical": {"weight": 0.25, "score": 0},
            "electrical": {"weight": 0.10, "score": 0},
            "safety": {"weight": 0.10, "score": 0},
            "tyres": {"weight": 0.10, "score": 0},
        }
    
    def score_condition(self, checklist: List[Dict], damage_marks: List[DamageMark]) -> Dict[str, Any]:
        """Score vehicle condition based on checklist and damage."""
        # Base scores from checklist
        total_items = len(checklist)
        passed_items = sum(1 for item in checklist if item.get("checked", False))
        base_score = (passed_items / max(total_items, 1)) * 100
        
        # Deduct for damage
        damage_score = len(damage_marks) * 5
        final_score = max(0, base_score - damage_score)
        
        # Determine grade
        if final_score >= 90:
            grade = ConditionGrade.A.value
            label = "Excellent"
        elif final_score >= 75:
            grade = ConditionGrade.B.value
            label = "Good"
        elif final_score >= 55:
            grade = ConditionGrade.C.value
            label = "Fair"
        elif final_score >= 35:
            grade = ConditionGrade.D.value
            label = "Poor"
        else:
            grade = ConditionGrade.E.value
            label = "Salvage"
        
        return {
            "score": round(final_score, 1),
            "grade": grade,
            "label": label,
            "passed_items": passed_items,
            "total_items": total_items,
            "completion_percentage": round((passed_items / max(total_items, 1)) * 100, 1),
            "damage_deduction": min(damage_score, 50),
        }

# ============================================================
# TOTAL LOSS ENGINE
# ============================================================

class TotalLossEngine:
    """Determines if a vehicle should be declared a total loss."""
    
    def __init__(self, threshold: float = 0.65):
        self.threshold = threshold
    
    def evaluate(self, repair_cost: float, market_value: float) -> Dict[str, Any]:
        """Evaluate if vehicle is a total loss."""
        loss_ratio = repair_cost / max(market_value, 1)
        total_loss = loss_ratio >= self.threshold
        
        if total_loss:
            decision = "Declare Total Loss"
            recommendation = "Vehicle is beyond economical repair. Proceed with salvage."
        else:
            decision = "Repair Recommended"
            recommendation = "Vehicle is economically repairable. Proceed with repairs."
        
        return {
            "total_loss": total_loss,
            "loss_ratio": round(loss_ratio, 2),
            "threshold": self.threshold,
            "decision": decision,
            "recommendation": recommendation,
            "repair_percentage": round(loss_ratio * 100, 1),
        }

# ============================================================
# SALVAGE VALUE ENGINE
# ============================================================

class SalvageEngine:
    """Calculates salvage value of a vehicle."""
    
    def calculate_salvage_value(self, vehicle: Vehicle, severity: str, parts_affected: List[str]) -> Dict[str, Any]:
        """Calculate salvage value."""
        salvage_percent = SALVAGE_PERCENTAGE.get(severity, 0.65)
        pre_accident_value = vehicle.market_value or 2000000
        
        salvage_value = pre_accident_value * salvage_percent
        
        # Adjust for major parts affected
        heavy_parts = ["engine", "transmission", "chassis"]
        if any(p in heavy_parts for p in parts_affected):
            salvage_value *= 0.80
        
        salvage_value = math.ceil(salvage_value / 100) * 100
        
        return {
            "salvage_value": salvage_value,
            "salvage_percentage": round(salvage_percent * 100, 1),
            "pre_accident_value": pre_accident_value,
            "value_loss": pre_accident_value - salvage_value,
            "recommendation": "Strip for parts" if salvage_value < 200000 else "Repair and resell"
        }

# ============================================================
# INSURANCE ASSESSMENT ENGINE
# ============================================================

class InsuranceAssessmentEngine:
    """Assesses insurance claims."""
    
    def assess_claim(self, repair_cost: float, market_value: float, policy_excess: float = 0) -> Dict[str, Any]:
        """Assess an insurance claim."""
        # Determine claim validity
        if repair_cost > market_value * 0.85:
            claim_valid = False
            reason = "Repair cost exceeds vehicle value"
        elif repair_cost < 10000:
            claim_valid = False
            reason = "Repair cost below excess threshold"
        else:
            claim_valid = True
            reason = "Claim approved"
        
        # Calculate payout (insurance typically covers 85% after excess)
        payout_ratio = 0.85
        gross_payout = repair_cost * payout_ratio
        net_payout = max(0, gross_payout - policy_excess)
        
        return {
            "claim_valid": claim_valid,
            "reason": reason,
            "gross_payout": math.ceil(gross_payout / 100) * 100,
            "net_payout": math.ceil(net_payout / 100) * 100,
            "policy_excess": policy_excess,
            "payout_ratio": payout_ratio,
        }

# ============================================================
# FRAUD DETECTION ENGINE
# ============================================================

class FraudDetectionEngine:
    """Detects potential fraud in assessments."""
    
    def __init__(self):
        self.fraud_indicators = []
    
    def analyze(self, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze assessment for fraud indicators."""
        flags = []
        score = 0
        
        # Check for duplicate claims
        if assessment_data.get("duplicate_claim"):
            flags.append("Duplicate claim detected")
            score += 30
        
        # Check for VIN manipulation
        if assessment_data.get("vin_manipulation"):
            flags.append("VIN manipulation suspected")
            score += 40
        
        # Check for odometer rollback
        if assessment_data.get("odometer_rollback"):
            flags.append("Odometer rollback detected")
            score += 35
        
        # Check for suspicious damage pattern
        if assessment_data.get("suspicious_damage"):
            flags.append("Suspicious damage pattern detected")
            score += 25
        
        # Check for inconsistent data
        if assessment_data.get("inconsistent_data"):
            flags.append("Inconsistent data found")
            score += 20
        
        # Determine risk level
        if score >= 70:
            risk = "HIGH"
        elif score >= 40:
            risk = "MEDIUM"
        else:
            risk = "LOW"
        
        return {
            "fraud_score": score,
            "risk_level": risk,
            "flags": flags,
            "requires_review": score >= 40,
            "recommendation": "Refer for investigation" if score >= 70 else "Proceed with assessment"
        }

# ============================================================
# RECOMMENDATION ENGINE
# ============================================================

class RecommendationEngine:
    """Generates recommendations based on assessment results."""
    
    def generate_recommendations(self, assessment_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations."""
        recommendations = []
        
        # Check if total loss
        if assessment_results.get("total_loss", False):
            recommendations.append("Declare vehicle as Total Loss")
            recommendations.append("Proceed with salvage processing")
            recommendations.append("Notify insurance company")
        else:
            recommendations.append("Proceed with repairs")
            recommendations.append("Obtain multiple repair quotes")
        
        # Condition-based recommendations
        if assessment_results.get("condition_grade") in ["D", "E"]:
            recommendations.append("Consider full mechanical inspection")
            recommendations.append("Review safety systems carefully")
        
        # Fraud recommendations
        if assessment_results.get("fraud_risk_level") == "HIGH":
            recommendations.append("Conduct detailed investigation")
            recommendations.append("Request additional documentation")
        
        # Add generic recommendations
        if assessment_results.get("confidence_score", 100) < 70:
            recommendations.append("Request additional images")
            recommendations.append("Schedule physical inspection if not done")
        
        return recommendations

# ============================================================
# REPORT GENERATOR ENGINE
# ============================================================

class ReportGenerator:
    """Generates professional assessment reports."""
    
    def generate_report(self, assessment_result: AssessmentResult) -> Dict[str, Any]:
        """Generate a complete assessment report."""
        report = {
            "assessment_id": assessment_result.assessment_id,
            "type": assessment_result.type,
            "generated_at": assessment_result.generated_at,
            "status": assessment_result.status,
            "vehicle": assessment_result.vehicle,
            "inspector": assessment_result.inspector,
            "summary": self._generate_summary(assessment_result),
            "details": self._generate_details(assessment_result),
            "recommendations": self._generate_recommendations(assessment_result),
            "verification": self._generate_verification(assessment_result),
        }
        return report
    
    def _generate_summary(self, result: AssessmentResult) -> Dict[str, Any]:
        """Generate executive summary."""
        return {
            "assessment_type": result.type.title().replace("_", " "),
            "vehicle_make": result.vehicle.get("make"),
            "vehicle_model": result.vehicle.get("model"),
            "vehicle_year": result.vehicle.get("year"),
            "total_repair_cost": result.repair_estimate.get("total_cost") if result.repair_estimate else None,
            "recommendation": result.recommendation or "Assessment Completed",
            "confidence_score": result.confidence_score,
        }
    
    def _generate_details(self, result: AssessmentResult) -> Dict[str, Any]:
        """Generate detailed assessment findings."""
        details = {
            "damage_analysis": {},
            "repair_estimate": result.repair_estimate,
            "valuation": {
                "market_value": result.vehicle.get("market_value"),
                "condition_grade": result.condition_grade,
            }
        }
        
        if result.total_loss is not None:
            details["total_loss"] = {
                "declared": result.total_loss,
                "loss_ratio": result.loss_ratio,
            }
        
        if result.salvage_value is not None:
            details["salvage"] = {
                "value": result.salvage_value,
            }
        
        return details
    
    def _generate_recommendations(self, result: AssessmentResult) -> List[str]:
        """Generate recommendations."""
        recs = []
        if result.recommendation:
            recs.append(result.recommendation)
        if result.total_loss:
            recs.append("Proceed with insurance claim processing")
        else:
            recs.append("Authorize repairs")
        return recs
    
    def _generate_verification(self, result: AssessmentResult) -> Dict[str, Any]:
        """Generate verification data."""
        return {
            "digital_signature": result.inspector.get("signature"),
            "inspector_name": result.inspector.get("name"),
            "verified_at": result.generated_at,
            "verification_token": hashlib.sha256(
                f"{result.assessment_id}{result.generated_at}".encode()
            ).hexdigest()[:16],
        }

# ============================================================
# QR VERIFICATION ENGINE
# ============================================================

class QRVerificationEngine:
    """Generates and verifies QR codes for reports."""
    
    def generate_qr_data(self, assessment_id: str, verification_token: str) -> str:
        """Generate QR code data."""
        return f"https://auto-v.co.ke/verify/{assessment_id}?token={verification_token}"
    
    def verify_report(self, assessment_id: str, verification_token: str, stored_token: str) -> bool:
        """Verify report authenticity."""
        return verification_token == stored_token

# ============================================================
# AUDIT TRAIL ENGINE
# ============================================================

class AuditTrailEngine:
    """Records all actions for compliance."""
    
    def __init__(self):
        self.audit_log = []
    
    def log_action(self, user: str, action: str, details: Dict[str, Any]):
        """Log an action."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "action": action,
            "details": details,
            "ip_address": details.get("ip_address", "N/A"),
            "device": details.get("device", "N/A"),
        }
        self.audit_log.append(entry)
        return entry
    
    def get_audit_trail(self, assessment_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for a specific assessment."""
        return [entry for entry in self.audit_log 
                if entry.get("details", {}).get("assessment_id") == assessment_id]

# ============================================================
# NOTIFICATION ENGINE
# ============================================================

class NotificationEngine:
    """Sends notifications via various channels."""
    
    def __init__(self):
        self.channels = ["email", "sms", "whatsapp", "push", "in_app"]
    
    def send_notification(self, recipient: str, message: str, channel: str = "email") -> Dict[str, Any]:
        """Send a notification."""
        if channel not in self.channels:
            return {"success": False, "error": f"Unsupported channel: {channel}"}
        
        # Mock sending - in production, integrate with actual providers
        return {
            "success": True,
            "channel": channel,
            "recipient": recipient,
            "sent_at": datetime.now().isoformat(),
        }

# ============================================================
# MAIN ASSESSMENT ENGINE - ORCHESTRATOR
# ============================================================

class AssessmentEngine:
    """Main orchestrator that coordinates all assessment modules."""
    
    def __init__(self):
        self.workflow = WorkflowEngine()
        self.vehicle_engine = VehicleIdentificationEngine()
        self.inspection_engine = InspectionValidationEngine()
        self.damage_engine = DamageAnalysisEngine()
        self.ai_engine = AIDamageEngine()
        self.repair_engine = RepairCostEngine()
        self.valuation_engine = ValuationEngine()
        self.condition_engine = ConditionScoringEngine()
        self.total_loss_engine = TotalLossEngine()
        self.salvage_engine = SalvageEngine()
        self.insurance_engine = InsuranceAssessmentEngine()
        self.fraud_engine = FraudDetectionEngine()
        self.recommendation_engine = RecommendationEngine()
        self.report_generator = ReportGenerator()
        self.qr_engine = QRVerificationEngine()
        self.audit_engine = AuditTrailEngine()
        self.notification_engine = NotificationEngine()
    
    def create_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new assessment."""
        assessment_id = self.workflow.generate_assessment_id()
        
        # Validate input
        is_valid, error = self.validate_assessment(data)
        if not is_valid:
            return {"error": error, "assessment_id": assessment_id}
        
        # Initialize state
        state = {
            "assessment_id": assessment_id,
            "workflow_state": "created",
            "created_at": datetime.now().isoformat(),
            "data": data,
        }
        
        # Log the creation
        self.audit_engine.log_action(
            user=data.get("inspector", {}).get("name", "System"),
            action="create_assessment",
            details={"assessment_id": assessment_id, "type": data.get("assessment_type")}
        )
        
        return state
    
    def validate_assessment(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate assessment data."""
        required = ["assessment_type", "vehicle", "inspector"]
        for field in required:
            if not data.get(field):
                return False, f"Missing required field: {field}"
        
        assessment_type = data.get("assessment_type")
        if assessment_type not in [t.value for t in AssessmentType]:
            return False, f"Invalid assessment type: {assessment_type}"
        
        vehicle = data.get("vehicle", {})
        if not vehicle.get("make") or not vehicle.get("model"):
            return False, "Vehicle make and model are required"
        
        return True, None
    
    def process_assessment(self, data: Dict[str, Any]) -> AssessmentResult:
        """Process a complete assessment."""
        # Step 1: Create and validate
        assessment = self.create_assessment(data)
        if "error" in assessment:
            raise ValueError(assessment["error"])
        
        # Step 2: Prepare vehicle
        vehicle = Vehicle(**data.get("vehicle", {}))
        vehicle = self.vehicle_engine.enrich_vehicle(vehicle)
        
        # Step 3: Process damage
        damage_marks = []
        for mark_data in data.get("damage_marks", []):
            damage_marks.append(DamageMark(**mark_data))
        
        damage_analysis = self.damage_engine.analyze_damage(damage_marks)
        
        # Step 4: Analyze images with AI
        ai_results = []
        if data.get("image_urls"):
            ai_results = self.ai_engine.analyze_batch(data.get("image_urls", []))
        
        # Step 5: Calculate repair cost
        repair_estimate = self.repair_engine.estimate_repair_cost(
            vehicle=vehicle,
            severity=damage_analysis.get("severity", "minor"),
            parts_affected=damage_analysis.get("parts_affected", [])
        )
        
        # Step 6: Calculate market valuation
        condition_score = self.condition_engine.score_condition(
            checklist=data.get("checklist", []),
            damage_marks=damage_marks
        )
        market_value = self.valuation_engine.calculate_market_value(
            vehicle=vehicle,
            condition_score=condition_score.get("score", 80)
        )
        
        # Step 7: Determine total loss
        total_loss_result = self.total_loss_engine.evaluate(
            repair_cost=repair_estimate["total_cost"],
            market_value=market_value
        )
        
        # Step 8: Calculate salvage value if applicable
        salvage_result = None
        if data.get("assessment_type") == AssessmentType.SALVAGE.value:
            salvage_result = self.salvage_engine.calculate_salvage_value(
                vehicle=vehicle,
                severity=damage_analysis.get("severity", "minor"),
                parts_affected=damage_analysis.get("parts_affected", [])
            )
        
        # Step 9: Process insurance claim if applicable
        insurance_result = None
        if data.get("assessment_type") == AssessmentType.INSURANCE_CLAIM.value:
            insurance_result = self.insurance_engine.assess_claim(
                repair_cost=repair_estimate["total_cost"],
                market_value=market_value,
                policy_excess=data.get("policy_excess", 0)
            )
        
        # Step 10: Detect fraud
        fraud_data = {
            "duplicate_claim": data.get("duplicate_claim", False),
            "vin_manipulation": not self.vehicle_engine.validate_vin(vehicle.vin) if vehicle.vin else False,
            "odometer_rollback": False,
            "suspicious_damage": damage_analysis.get("score", 0) > 90,
            "inconsistent_data": False,
        }
        fraud_result = self.fraud_engine.analyze(fraud_data)
        
        # Step 11: Build result
        inspector = Inspector(**data.get("inspector", {}))
        
        result = AssessmentResult(
            assessment_id=assessment["assessment_id"],
            type=data.get("assessment_type"),
            vehicle=asdict(vehicle),
            inspector=asdict(inspector),
            generated_at=datetime.now().isoformat(),
            repair_estimate=repair_estimate,
            confidence_score=90 - int(fraud_result.get("fraud_score", 0) / 3),
            total_loss=total_loss_result["total_loss"],
            loss_ratio=total_loss_result["loss_ratio"],
            condition_grade=condition_score.get("grade"),
            salvage_value=salvage_result.get("salvage_value") if salvage_result else None,
            estimated_payout=insurance_result.get("net_payout") if insurance_result else None,
            claim_valid=insurance_result.get("claim_valid") if insurance_result else None,
            damage_score=damage_analysis.get("score"),
            recommendation=total_loss_result["recommendation"],
        )
        
        # Step 12: Add fraud info
        result.fraud_risk = fraud_result.get("risk_level")
        result.fraud_flags = fraud_result.get("flags")
        
        # Step 13: Generate recommendations
        recommendations = self.recommendation_engine.generate_recommendations(asdict(result))
        result.recommendations = recommendations
        
        # Step 14: Log audit
        self.audit_engine.log_action(
            user=inspector.name,
            action="complete_assessment",
            details={"assessment_id": result.assessment_id}
        )
        
        # Step 15: Send notification
        self.notification_engine.send_notification(
            recipient=data.get("notification_email", "admin@autov.co.ke"),
            message=f"Assessment {result.assessment_id} completed",
            channel="email"
        )
        
        return result
    
    def get_assessment_price(self, assessment_type: str) -> int:
        """Get the price for a specific assessment type."""
        return ASSESSMENT_PRICES.get(assessment_type, 3000)
    
    def get_assessment_fields(self, assessment_type: str) -> List[Dict[str, Any]]:
        """Get required fields for a specific assessment type."""
        fields_map = {
            AssessmentType.ACCIDENT.value: [
                {"key": "incident_date", "label": "Incident Date", "type": "date", "required": True},
                {"key": "damage_severity", "label": "Damage Severity", "type": "select", 
                 "options": ["minor", "moderate", "major", "severe", "catastrophic"], "required": True},
                {"key": "parts_affected", "label": "Parts Affected", "type": "select", 
                 "options": ["engine", "transmission", "suspension", "brakes", "body", "paint", 
                            "electrical", "interior", "chassis", "tyres", "airbags", "cooling", 
                            "exhaust", "fuel_system", "steering"], "required": True, "multiple": True},
                {"key": "police_report", "label": "Police Report Number", "type": "text", "required": False},
                {"key": "location", "label": "Location", "type": "text", "required": False},
                {"key": "description", "label": "Description of Incident", "type": "textarea", "required": True}
            ],
            AssessmentType.INSURANCE_CLAIM.value: [
                {"key": "claim_number", "label": "Claim Number", "type": "text", "required": True},
                {"key": "insurance_company", "label": "Insurance Company", "type": "text", "required": True},
                {"key": "adjuster_name", "label": "Adjuster Name", "type": "text", "required": False},
                {"key": "policy_excess", "label": "Policy Excess (KES)", "type": "number", "required": False},
                {"key": "damage_severity", "label": "Damage Severity", "type": "select", 
                 "options": ["minor", "moderate", "major", "severe"], "required": True},
                {"key": "parts_affected", "label": "Parts Affected", "type": "select", 
                 "options": ["engine", "transmission", "suspension", "brakes", "body", "paint", 
                            "electrical", "interior", "chassis", "tyres"], "required": True, "multiple": True}
            ],
            AssessmentType.REPAIR_COST.value: [
                {"key": "damage_severity", "label": "Damage Severity", "type": "select", 
                 "options": ["minor", "moderate", "major", "severe"], "required": True},
                {"key": "parts_affected", "label": "Parts Affected", "type": "select", 
                 "options": ["engine", "transmission", "suspension", "brakes", "body", "paint", 
                            "electrical", "interior", "chassis", "tyres"], "required": True, "multiple": True},
                {"key": "labour_hours", "label": "Labour Hours", "type": "number", "required": False}
            ],
            AssessmentType.TOTAL_LOSS.value: [
                {"key": "repair_estimate", "label": "Repair Estimate (KES)", "type": "number", "required": True},
                {"key": "policy_details", "label": "Insurance Policy Details", "type": "text", "required": False},
                {"key": "salvage_value", "label": "Estimated Salvage Value (KES)", "type": "number", "required": False}
            ],
            AssessmentType.SALVAGE.value: [
                {"key": "damage_severity", "label": "Damage Severity", "type": "select", 
                 "options": ["minor", "moderate", "major", "severe", "catastrophic"], "required": True},
                {"key": "parts_affected", "label": "Parts Affected", "type": "select", 
                 "options": ["engine", "transmission", "suspension", "brakes", "body", "paint", 
                            "electrical", "interior", "chassis", "tyres"], "required": True, "multiple": True}
            ],
            AssessmentType.THEFT_RECOVERY.value: [
                {"key": "theft_date", "label": "Theft Date", "type": "date", "required": True},
                {"key": "recovery_date", "label": "Recovery Date", "type": "date", "required": True},
                {"key": "police_station", "label": "Police Station", "type": "text", "required": True},
                {"key": "condition", "label": "Condition on Recovery", "type": "select", 
                 "options": ["excellent", "good", "fair", "poor", "damaged"], "required": True},
                {"key": "modifications", "label": "Modifications", "type": "text", "required": False}
            ]
        }
        return fields_map.get(assessment_type, [])


# ============================================================
# FACTORY FUNCTION - CREATE ASSESSMENT ENGINE INSTANCE
# ============================================================

def create_assessment_engine() -> AssessmentEngine:
    """Factory function to create a new AssessmentEngine instance."""
    return AssessmentEngine()


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    # Create engine instance
    engine = create_assessment_engine()
    
    # Sample assessment data
    sample_data = {
        "assessment_type": "accident",
        "vehicle": {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "reg_number": "KCA 123A",
            "vin": "JTEGD34V000123456",
            "odometer": 45000,
            "market_value": 2500000,
            "body_type": "Sedan",
            "fuel_type": "Petrol",
            "transmission": "Manual",
            "engine_capacity": 1800,
            "colour": "White"
        },
        "inspector": {
            "name": "John Assessor",
            "credentials": "AVM-12345",
            "reg_number": "INS-2024-001",
            "company": "AUTO-V Assessors",
            "signature": "John Assessor"
        },
        "damage_marks": [
            {"panel": "Front Bumper", "damage_type": "dent", "severity": "moderate"},
            {"panel": "Left Fender", "damage_type": "scratch", "severity": "minor"}
        ],
        "checklist": [
            {"item": "Engine", "checked": True},
            {"item": "Brakes", "checked": True},
            {"item": "Suspension", "checked": False}
        ],
        "image_urls": ["image1.jpg", "image2.jpg"],
        "incident_date": "2025-01-15",
        "location": "Nairobi",
        "damage_severity": "moderate",
        "parts_affected": ["body", "paint", "suspension"],
        "police_report": "POL-2025-001234",
        "description": "Side impact collision at low speed"
    }
    
    print("=" * 60)
    print("AUTO-V ASSESSMENT ENGINE")
    print("=" * 60)
    
    # Process assessment
    result = engine.process_assessment(sample_data)
    
    print(f"\nAssessment ID: {result.assessment_id}")
    print(f"Type: {result.type}")
    print(f"Confidence Score: {result.confidence_score}%")
    print(f"Condition Grade: {result.condition_grade}")
    print(f"Repair Cost: KES {result.repair_estimate['total_cost']:,}")
    print(f"Total Loss: {result.total_loss}")
    print(f"Recommendation: {result.recommendation}")
    
    if result.fraud_risk:
        print(f"Fraud Risk: {result.fraud_risk}")
    
    print("\n--- Full Result ---")
    print(json.dumps(result.to_dict(), indent=2, default=str))
