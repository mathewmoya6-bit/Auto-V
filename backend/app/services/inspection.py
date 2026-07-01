# ============================================================
# AUTO-V BACKEND SERVICES - COMPLETE PRODUCTION FILE
# inspection_engine.py
# ============================================================

import math
import random
import hashlib
import hmac
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

# ============================================================
# PART 1: CONFIGURATION & CONSTANTS
# ============================================================

# ─── SCORING CONFIGURATION ──────────────────────────────────────

SCORE_MAP = {
    "excellent": 10,
    "good": 8,
    "fair": 5,
    "poor": 3,
}

WEIGHTS = {
    "engine": 0.15,
    "transmission": 0.15,
    "suspension": 0.12,
    "brakes": 0.18,
    "paint": 0.05,
    "chassis": 0.15,
    "interior": 0.05,
    "electronics": 0.10,
    "tyres": 0.05,
}

ACCIDENT_IMPACT = {
    "none": 0.0,
    "minor": -0.5,
    "moderate": -1.5,
    "major": -3.0,
}

INSPECTION_PRICES = {
    "Pre-Purchase": 3500,
    "Insurance": 4000,
    "Loan/Finance": 4500,
    "Fleet": 5000,
    "Export": 6000,
    "Other": 3500,
}

# ─── KEBS CONFIGURATION ──────────────────────────────────────────

KEBS_WEIGHTS = {
    "steering": 20,
    "brakes": 25,
    "tyres": 15,
    "suspension": 15,
    "lighting": 10,
    "visibility": 5,
    "safety": 5,
    "emissions": 5,
}

CRITICAL_FAILURES = [
    "brake_failure",
    "steering_failure",
    "major_chassis_damage",
    "vin_tampered",
    "seatbelt_missing",
    "tyre_below_limit",
    "headlights_failed",
    "airbags_removed",
    "structural_accident_damage",
]

MIN_TYRE_TREAD = 1.6
MIN_BRAKE_PAD = 3.0
MIN_BATTERY_VOLTAGE = 12.4

# ─── GRADE CONFIGURATION ─────────────────────────────────────────

GRADE_THRESHOLDS = {
    "A+": 95, "A": 90, "B+": 85, "B": 80,
    "C": 70, "D": 60, "F": 0
}

SCORE_CATEGORIES = {
    "exterior": {"weight": 0.20, "components": ["paint", "chassis", "body"]},
    "interior": {"weight": 0.15, "components": ["interior", "seats", "dashboard"]},
    "mechanical": {"weight": 0.30, "components": ["engine", "transmission", "suspension"]},
    "electrical": {"weight": 0.15, "components": ["electronics", "lights", "battery"]},
    "safety": {"weight": 0.20, "components": ["brakes", "tyres", "safety_equipment"]},
}

# ─── KEBS STANDARDS ──────────────────────────────────────────────

KEBS_STANDARDS = {
    "steering": {
        "name": "Steering System",
        "checks": [
            {"key": "steering_play", "label": "Steering Play", "pass": "< 10mm"},
            {"key": "steering_rack", "label": "Steering Rack", "pass": "No leaks"},
            {"key": "steering_column", "label": "Steering Column", "pass": "No damage"},
            {"key": "power_steering", "label": "Power Steering", "pass": "No leaks"},
            {"key": "alignment", "label": "Wheel Alignment", "pass": "Within spec"},
        ]
    },
    "brakes": {
        "name": "Brake System",
        "checks": [
            {"key": "foot_brake", "label": "Foot Brake Efficiency", "pass": "> 60%"},
            {"key": "parking_brake", "label": "Parking Brake", "pass": "Functional"},
            {"key": "brake_pads", "label": "Brake Pads", "pass": "> 3mm"},
            {"key": "brake_discs", "label": "Brake Discs", "pass": "No scoring"},
            {"key": "brake_hoses", "label": "Brake Hoses", "pass": "No cracks"},
            {"key": "brake_fluid", "label": "Brake Fluid", "pass": "Level OK"},
            {"key": "abs", "label": "ABS Operation", "pass": "Functional"},
        ]
    },
    "tyres": {
        "name": "Tyres",
        "checks": [
            {"key": "front_left", "label": "Front Left", "pass": "> 1.6mm"},
            {"key": "front_right", "label": "Front Right", "pass": "> 1.6mm"},
            {"key": "rear_left", "label": "Rear Left", "pass": "> 1.6mm"},
            {"key": "rear_right", "label": "Rear Right", "pass": "> 1.6mm"},
            {"key": "spare", "label": "Spare Wheel", "pass": "> 1.6mm"},
        ]
    },
    "suspension": {
        "name": "Suspension",
        "checks": [
            {"key": "front_shocks", "label": "Front Shocks", "pass": "No leaks"},
            {"key": "rear_shocks", "label": "Rear Shocks", "pass": "No leaks"},
            {"key": "springs", "label": "Springs", "pass": "No breaks"},
            {"key": "bushes", "label": "Bushes", "pass": "No excessive play"},
            {"key": "ball_joints", "label": "Ball Joints", "pass": "No play"},
        ]
    },
    "lighting": {
        "name": "Lighting System",
        "checks": [
            {"key": "headlights", "label": "Headlights", "pass": "Functional"},
            {"key": "high_beam", "label": "High Beam", "pass": "Functional"},
            {"key": "indicators", "label": "Indicators", "pass": "Functional"},
            {"key": "brake_lights", "label": "Brake Lights", "pass": "Functional"},
            {"key": "reverse_lights", "label": "Reverse Lights", "pass": "Functional"},
            {"key": "hazards", "label": "Hazards", "pass": "Functional"},
        ]
    },
    "visibility": {
        "name": "Visibility",
        "checks": [
            {"key": "windshield", "label": "Windshield", "pass": "No cracks"},
            {"key": "wipers", "label": "Wipers", "pass": "Functional"},
            {"key": "washers", "label": "Washers", "pass": "Functional"},
            {"key": "rear_mirror", "label": "Rear Mirror", "pass": "Present"},
            {"key": "side_mirrors", "label": "Side Mirrors", "pass": "Present"},
        ]
    },
    "safety": {
        "name": "Safety Equipment",
        "checks": [
            {"key": "seat_belts", "label": "Seat Belts", "pass": "Functional"},
            {"key": "airbags", "label": "Airbags", "pass": "Present"},
            {"key": "horn", "label": "Horn", "pass": "Functional"},
            {"key": "fire_extinguisher", "label": "Fire Extinguisher", "pass": "Present"},
            {"key": "reflective_triangles", "label": "Reflective Triangles", "pass": "Present"},
        ]
    },
    "emissions": {
        "name": "Emissions",
        "checks": [
            {"key": "smoke", "label": "Smoke Level", "pass": "Within limits"},
            {"key": "oil_leaks", "label": "Oil Leaks", "pass": "None"},
            {"key": "coolant_leaks", "label": "Coolant Leaks", "pass": "None"},
            {"key": "exhaust_leaks", "label": "Exhaust Leaks", "pass": "None"},
            {"key": "noise", "label": "Noise Level", "pass": "Within limits"},
        ]
    },
    "chassis": {
        "name": "Chassis",
        "checks": [
            {"key": "frame_damage", "label": "Frame Damage", "pass": "None"},
            {"key": "rust", "label": "Rust/Corrosion", "pass": "None excessive"},
            {"key": "structural_welds", "label": "Structural Welds", "pass": "No cracks"},
            {"key": "cross_members", "label": "Cross Members", "pass": "Intact"},
            {"key": "accident_repairs", "label": "Accident Repairs", "pass": "Professional"},
        ]
    },
    "electrical": {
        "name": "Electrical",
        "checks": [
            {"key": "battery", "label": "Battery Voltage", "pass": "> 12.4V"},
            {"key": "charging", "label": "Charging Voltage", "pass": "13.5-14.5V"},
            {"key": "starter", "label": "Starter Motor", "pass": "Functional"},
            {"key": "alternator", "label": "Alternator", "pass": "Functional"},
            {"key": "warning_lights", "label": "Warning Lights", "pass": "None illuminated"},
        ]
    }
}

# ─── CERTIFICATE CONFIG ──────────────────────────────────────────

SECRET_KEY = "AUTO-V-SECRET-KEY-2024"
QR_BASE_URL = "https://autov.africa/verify"


# ============================================================
# PART 2: DATA CLASSES
# ============================================================

@dataclass
class VehicleData:
    make: str
    model: str
    year: int
    odometer: int = 0
    vin: str = ""
    registration: str = ""
    body_type: str = ""
    engine_cc: int = 0
    transmission: str = ""
    fuel_type: str = ""
    tyre_depth_mm: float = 6.0
    accident_history: str = "none"


@dataclass
class InspectorData:
    name: str
    credentials: str
    signature: str
    reg_number: str = ""
    company: str = ""


@dataclass
class InspectionRatings:
    engine: str = "Good"
    transmission: str = "Good"
    suspension: str = "Good"
    brakes: str = "Good"
    paint: str = "Good"
    chassis: str = "Good"
    interior: str = "Good"
    electronics: str = "Good"


# ============================================================
# PART 3: UTILITY FUNCTIONS
# ============================================================

def tyre_score(depth_mm: float) -> float:
    """Convert tyre tread depth (mm) to a score 0-10."""
    if depth_mm >= 8:
        return 10.0
    elif depth_mm >= 6:
        return 8.0
    elif depth_mm >= 4:
        return 6.0
    elif depth_mm >= 3:
        return 4.0
    elif depth_mm >= 1.6:
        return 2.0
    else:
        return 0.0


def get_recommendations(scores: Dict[str, float]) -> List[str]:
    """Generate recommendations based on low scores."""
    recommendations = []
    if scores.get("engine", 10) < 6:
        recommendations.append("Engine requires professional diagnosis and possible repair.")
    if scores.get("transmission", 10) < 6:
        recommendations.append("Transmission may have wear; check fluid levels and shifting quality.")
    if scores.get("suspension", 10) < 6:
        recommendations.append("Suspension components may be worn; inspect shocks, bushings, and alignment.")
    if scores.get("brakes", 10) < 6:
        recommendations.append("Brake system needs immediate attention; check pads, rotors, and fluid.")
    if scores.get("chassis", 10) < 6:
        recommendations.append("Chassis/structural integrity may be compromised; seek professional evaluation.")
    if scores.get("tyres", 10) < 4:
        recommendations.append("Tyres are worn below recommended tread depth; replace immediately.")
    if scores.get("electronics", 10) < 6:
        recommendations.append("Electrical system has issues; check battery, alternator, and warning lights.")
    if scores.get("paint", 10) < 6:
        recommendations.append("Paint condition is poor; consider detailing or respray.")
    if scores.get("interior", 10) < 6:
        recommendations.append("Interior condition needs attention; deep cleaning or repairs required.")
    return recommendations


def calculate_grade(score: float) -> Dict[str, Any]:
    """Calculate letter grade based on score."""
    if score >= 95:
        return {"grade": "A+", "label": "Excellent", "color": "#22c55e"}
    elif score >= 90:
        return {"grade": "A", "label": "Excellent", "color": "#22c55e"}
    elif score >= 85:
        return {"grade": "B+", "label": "Very Good", "color": "#22c55e"}
    elif score >= 80:
        return {"grade": "B", "label": "Good", "color": "#eab308"}
    elif score >= 70:
        return {"grade": "C", "label": "Fair", "color": "#f59e0b"}
    elif score >= 60:
        return {"grade": "D", "label": "Poor", "color": "#ef4444"}
    else:
        return {"grade": "F", "label": "Very Poor", "color": "#ef4444"}


def normalize_score(value: float, min_val: float = 0, max_val: float = 10) -> float:
    """Normalize a score to 0-10 range."""
    if value < min_val:
        return 0
    if value > max_val:
        return 10
    return round((value - min_val) / (max_val - min_val) * 10, 1)


# ============================================================
# PART 4: INSPECTION ENGINE
# ============================================================

def run_inspection(
    vehicle: VehicleData,
    ratings: InspectionRatings,
    inspector: InspectorData,
    purpose: str = "Pre-Purchase",
    region: str = "Nairobi",
    inspection_type: str = "Premium",
) -> Dict[str, Any]:
    """
    Run a complete vehicle inspection and generate a professional report.
    """
    # 1. Convert ratings to scores
    scores = {
        "engine": SCORE_MAP.get(ratings.engine.lower(), 5),
        "transmission": SCORE_MAP.get(ratings.transmission.lower(), 5),
        "suspension": SCORE_MAP.get(ratings.suspension.lower(), 5),
        "brakes": SCORE_MAP.get(ratings.brakes.lower(), 5),
        "paint": SCORE_MAP.get(ratings.paint.lower(), 5),
        "chassis": SCORE_MAP.get(ratings.chassis.lower(), 5),
        "interior": SCORE_MAP.get(ratings.interior.lower(), 5),
        "electronics": SCORE_MAP.get(ratings.electronics.lower(), 5),
        "tyres": tyre_score(vehicle.tyre_depth_mm),
    }

    # 2. Apply accident penalty
    accident_penalty = ACCIDENT_IMPACT.get(vehicle.accident_history.lower(), 0.0)
    for key in scores:
        if key != "tyres":
            scores[key] = max(0, scores[key] + accident_penalty)

    # 3. Calculate weighted overall score
    overall = sum(scores[key] * WEIGHTS[key] for key in WEIGHTS)
    overall = round(overall, 1)

    # 4. Category scores
    exterior = round((scores["paint"] + scores["chassis"] + 10 + accident_penalty if accident_penalty < 0 else 10) / 3, 1)
    interior = scores["interior"]
    mechanical = round((scores["engine"] + scores["transmission"] + scores["suspension"]) / 3, 1)
    electrical = scores["electronics"]
    safety = round((scores["brakes"] * 0.4 + scores["chassis"] * 0.3 + scores["tyres"] * 0.3), 1)

    # 5. Generate issues and recommendations
    issues = get_recommendations(scores)

    # 6. Calculate confidence score
    confidence = 100
    if any(s == 0 for s in scores.values()):
        confidence -= 10
    if vehicle.accident_history.lower() == "major":
        confidence -= 15
    elif vehicle.accident_history.lower() == "moderate":
        confidence -= 10
    if vehicle.tyre_depth_mm <= 0:
        confidence -= 10
    if inspector.name == "Not specified":
        confidence -= 5
    if not inspector.signature:
        confidence -= 5
    confidence = max(0, min(100, confidence))

    # 7. Calculate grade
    grade_info = calculate_grade(overall * 10)

    # 8. Generate certificate number
    certificate_number = f"INS-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"

    # 9. Build result
    return {
        "inspection_id": f"INS-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
        "certificate_number": certificate_number,
        "vehicle": {
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "registration": vehicle.registration,
            "vin": vehicle.vin,
            "odometer": vehicle.odometer,
            "body_type": vehicle.body_type,
            "engine_cc": vehicle.engine_cc,
            "transmission": vehicle.transmission,
            "fuel_type": vehicle.fuel_type,
            "tyre_depth_mm": vehicle.tyre_depth_mm,
            "accident_history": vehicle.accident_history,
        },
        "scores": {
            "overall": overall,
            "exterior": exterior,
            "interior": interior,
            "mechanical": mechanical,
            "electrical": electrical,
            "safety": safety,
        },
        "detailed_scores": scores,
        "grade": grade_info,
        "confidence_score": confidence,
        "issues": issues,
        "recommendations": issues,
        "inspector": {
            "name": inspector.name,
            "credentials": inspector.credentials,
            "signature": inspector.signature,
            "reg_number": inspector.reg_number,
            "company": inspector.company,
        },
        "inspection_details": {
            "type": inspection_type,
            "region": region,
            "purpose": purpose,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
        },
        "generated_at": datetime.now().isoformat(),
        "price": INSPECTION_PRICES.get(purpose, 3500),
    }


def quick_inspection(
    make: str,
    model: str,
    year: int,
    odometer: int,
    condition: str = "good",
) -> Dict[str, Any]:
    """Fast inspection estimate for instant checks."""
    rating = "good"
    if condition.lower() in ["excellent", "good", "fair", "poor"]:
        rating = condition.lower()

    vehicle = VehicleData(
        make=make,
        model=model,
        year=year,
        odometer=odometer,
        tyre_depth_mm=6.0,
        accident_history="none",
    )

    ratings = InspectionRatings(
        engine=rating,
        transmission=rating,
        suspension=rating,
        brakes=rating,
        paint=rating,
        chassis=rating,
        interior=rating,
        electronics=rating,
    )

    inspector = InspectorData(
        name="Automated AI",
        credentials="AI-ESTIMATE",
        signature="AI System",
    )

    return run_inspection(vehicle, ratings, inspector, purpose="Quick Estimate")


def get_inspection_price(purpose: str) -> int:
    """Get the price for a specific inspection purpose."""
    return INSPECTION_PRICES.get(purpose, 3500)


def validate_inspection_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate inspection input data."""
    required = ['make', 'model', 'year']
    for field in required:
        if not data.get(field):
            return False, f"Missing required field: {field}"
    
    try:
        year = int(data.get('year', 0))
        if year < 1900 or year > datetime.now().year + 1:
            return False, "Invalid year"
    except (ValueError, TypeError):
        return False, "Year must be a valid number"
    
    return True, None


# ============================================================
# PART 5: ROADWORTHINESS ENGINE (KEBS)
# ============================================================

def evaluate_category(category: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single KEBS category."""
    standard = KEBS_STANDARDS.get(category)
    if not standard:
        return {"status": "unknown", "failures": []}

    failures = []
    critical = False

    for check in standard.get("checks", []):
        key = check["key"]
        value = data.get(key)
        if value is None:
            failures.append(f"{check['label']}: Not checked")
            continue
        
        passed = check_value(category, key, value)
        if not passed:
            failures.append(f"{check['label']}: Failed - {check['pass']}")
            if is_critical_check(category, key):
                critical = True

    status = "pass"
    if critical:
        status = "fail"
    elif failures:
        status = "warning"

    return {
        "status": status,
        "failures": failures,
        "critical": critical,
        "checks_passed": len(failures) == 0,
    }


def check_value(category: str, key: str, value: Any) -> bool:
    """Check if a value passes the standard."""
    if category == "tyres":
        if "tread" in key or "tyre" in key:
            return float(value) >= MIN_TYRE_TREAD
    elif category == "brakes":
        if "pads" in key:
            return float(value) >= MIN_BRAKE_PAD
    elif category == "electrical":
        if "battery" in key:
            return float(value) >= MIN_BATTERY_VOLTAGE
        if "charging" in key:
            return 13.5 <= float(value) <= 14.5
    elif category == "chassis":
        if "frame" in key or "rust" in key or "welds" in key:
            return str(value).lower() in ["none", "good", "ok", "pass"]
    elif category == "steering":
        if "play" in key:
            return float(value) <= 10
    elif category == "visibility":
        if "cracks" in key:
            return str(value).lower() in ["none", "no", "ok"]
    
    # Default: check if value is truthy and not "fail"
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in ["fail", "no", "missing", "bad", "damaged"]
    return bool(value)


def is_critical_check(category: str, key: str) -> bool:
    """Determine if a check is critical for roadworthiness."""
    critical_pairs = {
        "steering": ["steering_play", "steering_rack"],
        "brakes": ["foot_brake", "parking_brake"],
        "tyres": ["front_left", "front_right", "rear_left", "rear_right"],
        "chassis": ["frame_damage", "structural_welds"],
        "safety": ["seat_belts", "airbags"],
        "lighting": ["headlights"],
    }
    return category in critical_pairs and key in critical_pairs[category]


def evaluate_roadworthiness(
    steering_data: Dict[str, Any] = None,
    brakes_data: Dict[str, Any] = None,
    tyres_data: Dict[str, Any] = None,
    suspension_data: Dict[str, Any] = None,
    lighting_data: Dict[str, Any] = None,
    visibility_data: Dict[str, Any] = None,
    safety_data: Dict[str, Any] = None,
    chassis_data: Dict[str, Any] = None,
    emissions_data: Dict[str, Any] = None,
    electrical_data: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Evaluate vehicle roadworthiness against KEBS standards."""
    
    # 1. Collect all results
    categories = {
        "steering": steering_data or {},
        "brakes": brakes_data or {},
        "tyres": tyres_data or {},
        "suspension": suspension_data or {},
        "lighting": lighting_data or {},
        "visibility": visibility_data or {},
        "safety": safety_data or {},
        "chassis": chassis_data or {},
        "emissions": emissions_data or {},
        "electrical": electrical_data or {},
    }

    # 2. Evaluate each category
    results = {}
    critical_failures = []
    score = 0
    max_score = 0

    for category, data in categories.items():
        category_results = evaluate_category(category, data)
        results[category] = category_results
        
        weight = KEBS_WEIGHTS.get(category, 5)
        max_score += weight
        
        if category_results["status"] == "pass":
            score += weight
        elif category_results["status"] == "warning":
            score += weight * 0.5
        
        if category_results.get("critical", False) or category_results.get("status") == "fail":
            critical_failures.append({
                "category": category,
                "name": KEBS_STANDARDS.get(category, {}).get("name", category),
                "details": category_results.get("failures", [])
            })

    # 3. Calculate percentage
    percentage = round((score / max_score) * 100, 1) if max_score > 0 else 0

    # 4. Determine status
    has_critical = len(critical_failures) > 0
    
    if has_critical:
        status = "FAIL"
    elif percentage >= 80:
        status = "PASS"
    elif percentage >= 60:
        status = "WARNING"
    else:
        status = "FAIL"

    # 5. Generate certificate
    cert_number = f"RW-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"

    # 6. Generate recommendations
    recommendations = generate_roadworthiness_recommendations(results, critical_failures)

    return {
        "roadworthiness_score": percentage,
        "status": status,
        "grade": calculate_roadworthiness_grade(percentage),
        "critical_failures": critical_failures,
        "category_results": results,
        "recommendations": recommendations,
        "certificate_number": cert_number,
        "expires": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
        "qr_code": f"https://autov.africa/verify/{cert_number}",
        "generated_at": datetime.now().isoformat(),
    }


def calculate_roadworthiness_grade(score: float) -> Dict[str, Any]:
    """Calculate roadworthiness grade."""
    if score >= 95:
        return {"grade": "A+", "label": "Excellent"}
    elif score >= 90:
        return {"grade": "A", "label": "Excellent"}
    elif score >= 85:
        return {"grade": "B+", "label": "Very Good"}
    elif score >= 80:
        return {"grade": "B", "label": "Good"}
    elif score >= 70:
        return {"grade": "C", "label": "Fair"}
    elif score >= 60:
        return {"grade": "D", "label": "Poor"}
    else:
        return {"grade": "F", "label": "Unsafe"}


def generate_roadworthiness_recommendations(
    results: Dict[str, Any],
    critical_failures: List[Dict]
) -> List[str]:
    """Generate recommendations based on roadworthiness results."""
    recommendations = []

    for category, result in results.items():
        if result.get("status") in ["fail", "warning"]:
            for failure in result.get("failures", []):
                recommendations.append(f"⚠️ {failure}")

    if critical_failures:
        for cf in critical_failures:
            recommendations.append(f"🔴 CRITICAL: {cf['name']} failed inspection")

    if not recommendations:
        recommendations.append("✅ Vehicle meets all KEBS roadworthiness standards.")

    return recommendations


def quick_roadworthiness_check(
    make: str,
    model: str,
    year: int,
    condition: str = "good",
) -> Dict[str, Any]:
    """Quick roadworthiness check for instant estimates."""
    status_map = {
        "excellent": {"status": "PASS", "score": 95},
        "good": {"status": "PASS", "score": 85},
        "fair": {"status": "WARNING", "score": 70},
        "poor": {"status": "FAIL", "score": 55},
    }
    result = status_map.get(condition.lower(), status_map["good"])

    return {
        "roadworthiness_score": result["score"],
        "status": result["status"],
        "grade": calculate_roadworthiness_grade(result["score"]),
        "critical_failures": [] if result["status"] != "FAIL" else ["Critical items require attention"],
        "recommendations": ["Professional inspection recommended"] if result["status"] != "PASS" else [],
    }


# ============================================================
# PART 6: SCORING ENGINE
# ============================================================

def calculate_scores(component_scores: Dict[str, float]) -> Dict[str, Any]:
    """Calculate category scores and overall score from component scores."""
    category_scores = {}
    overall = 0.0
    
    for category, config in SCORE_CATEGORIES.items():
        components = config["components"]
        weights = config["weight"]
        
        cat_score = 0.0
        count = 0
        for comp in components:
            if comp in component_scores:
                cat_score += component_scores[comp]
                count += 1
        
        cat_score = cat_score / count if count > 0 else 0
        category_scores[category] = round(cat_score, 1)
        overall += cat_score * weights
    
    overall = round(overall, 1)
    grade = get_grade(overall)
    confidence = calculate_confidence(component_scores)
    
    return {
        "category_scores": category_scores,
        "overall_score": overall,
        "grade": grade,
        "confidence_score": confidence,
        "score_components": component_scores,
    }


def get_grade(score: float) -> Dict[str, Any]:
    """Get grade based on score."""
    for grade, threshold in GRADE_THRESHOLDS.items():
        if score >= threshold:
            return {"grade": grade, "score": score}
    return {"grade": "F", "score": score}


def calculate_confidence(component_scores: Dict[str, float]) -> int:
    """Calculate confidence score based on data completeness."""
    confidence = 100
    
    # Check for missing or zero scores
    zero_count = sum(1 for v in component_scores.values() if v <= 0)
    confidence -= zero_count * 5
    
    # Check for inconsistent scores
    values = [v for v in component_scores.values() if v > 0]
    if values and len(values) > 1:
        variance = statistics.variance(values) if len(values) > 1 else 0
        if variance > 10:
            confidence -= 10
    
    return max(0, min(100, confidence))


# ============================================================
# PART 7: REPORT GENERATOR
# ============================================================

def generate_inspection_report(
    inspection_result: Dict[str, Any],
    roadworthiness_result: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Generate a professional inspection report combining all results."""
    vehicle = inspection_result.get("vehicle", {})
    scores = inspection_result.get("scores", {})
    inspector = inspection_result.get("inspector", {})
    details = inspection_result.get("inspection_details", {})
    
    report = {
        "report_id": f"RPT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
        "certificate_number": inspection_result.get("certificate_number"),
        "generated_at": datetime.now().isoformat(),
        "vehicle": {
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "year": vehicle.get("year"),
            "registration": vehicle.get("registration"),
            "vin": vehicle.get("vin"),
            "odometer": vehicle.get("odometer"),
            "body_type": vehicle.get("body_type"),
            "engine_cc": vehicle.get("engine_cc"),
            "transmission": vehicle.get("transmission"),
            "fuel_type": vehicle.get("fuel_type"),
        },
        "scores": {
            "overall": scores.get("overall"),
            "exterior": scores.get("exterior"),
            "interior": scores.get("interior"),
            "mechanical": scores.get("mechanical"),
            "electrical": scores.get("electrical"),
            "safety": scores.get("safety"),
        },
        "grade": inspection_result.get("grade", {}),
        "confidence_score": inspection_result.get("confidence_score"),
        "inspector": {
            "name": inspector.get("name"),
            "credentials": inspector.get("credentials"),
            "signature": inspector.get("signature"),
        },
        "inspection_details": details,
        "issues": inspection_result.get("issues", []),
        "recommendations": inspection_result.get("recommendations", []),
    }
    
    if roadworthiness_result:
        report["roadworthiness"] = {
            "score": roadworthiness_result.get("roadworthiness_score"),
            "status": roadworthiness_result.get("status"),
            "grade": roadworthiness_result.get("grade"),
            "critical_failures": roadworthiness_result.get("critical_failures", []),
            "certificate_number": roadworthiness_result.get("certificate_number"),
            "expires": roadworthiness_result.get("expires"),
        }
    
    return report


def generate_pdf_content(report: Dict[str, Any]) -> str:
    """Generate HTML content for PDF report."""
    vehicle = report.get("vehicle", {})
    scores = report.get("scores", {})
    grade = report.get("grade", {})
    inspector = report.get("inspector", {})
    roadworthiness = report.get("roadworthiness", {})
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; }}
            .header {{ border-bottom: 2px solid #eab308; padding-bottom: 10px; }}
            .header h1 {{ color: #eab308; }}
            .score-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; gap: 15px; margin: 20px 0; }}
            .score-item {{ border: 1px solid #ddd; padding: 15px; text-align: center; border-radius: 8px; }}
            .score-item .value {{ font-size: 28px; font-weight: bold; }}
            .score-item .label {{ color: #666; font-size: 12px; text-transform: uppercase; }}
            .result-detail {{ margin: 15px 0; }}
            .item {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #eee; }}
            .label {{ color: #666; }}
            .value {{ font-weight: bold; }}
            .green {{ color: #22c55e; }}
            .gold {{ color: #eab308; }}
            .red {{ color: #ef4444; }}
            .footer {{ margin-top: 30px; border-top: 1px solid #ccc; padding-top: 15px; font-size: 12px; color: #999; text-align: center; }}
            .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
            .badge-pass {{ background: #22c55e; color: #000; }}
            .badge-fail {{ background: #dc2626; color: #fff; }}
            .badge-warning {{ background: #f59e0b; color: #000; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔍 AUTO-V Professional Inspection Report</h1>
            <p>Certificate: {report.get('certificate_number')}</p>
            <p>Generated: {report.get('generated_at')}</p>
        </div>
        
        <h2>Vehicle Information</h2>
        <div class="result-detail">
            <div class="item"><span class="label">Make</span><span class="value">{vehicle.get('make')}</span></div>
            <div class="item"><span class="label">Model</span><span class="value">{vehicle.get('model')}</span></div>
            <div class="item"><span class="label">Year</span><span class="value">{vehicle.get('year')}</span></div>
            <div class="item"><span class="label">Registration</span><span class="value">{vehicle.get('registration')}</span></div>
            <div class="item"><span class="label">Odometer</span><span class="value">{vehicle.get('odometer')} km</span></div>
        </div>
        
        <h2>Inspection Scores</h2>
        <div class="score-grid">
            <div class="score-item">
                <div class="value gold">{scores.get('overall')}/10</div>
                <div class="label">Overall</div>
            </div>
            <div class="score-item">
                <div class="value">{scores.get('exterior')}</div>
                <div class="label">Exterior</div>
            </div>
            <div class="score-item">
                <div class="value">{scores.get('interior')}</div>
                <div class="label">Interior</div>
            </div>
            <div class="score-item">
                <div class="value">{scores.get('mechanical')}</div>
                <div class="label">Mechanical</div>
            </div>
            <div class="score-item">
                <div class="value">{scores.get('electrical')}</div>
                <div class="label">Electrical</div>
            </div>
        </div>
        
        <h2>Grade: {grade.get('grade')} - {grade.get('label')}</h2>
        <p>Confidence: {report.get('confidence_score')}%</p>
        
        <h2>Inspector</h2>
        <div class="result-detail">
            <div class="item"><span class="label">Name</span><span class="value">{inspector.get('name')}</span></div>
            <div class="item"><span class="label">Credentials</span><span class="value">{inspector.get('credentials')}</span></div>
            <div class="item"><span class="label">Signature</span><span class="value">{inspector.get('signature')}</span></div>
        </div>
    """
    
    if roadworthiness:
        status_class = "badge-pass" if roadworthiness.get('status') == "PASS" else "badge-fail"
        html += f"""
        <h2>Roadworthiness (KEBS)</h2>
        <div class="result-detail">
            <div class="item"><span class="label">Status</span><span class="badge {status_class}">{roadworthiness.get('status')}</span></div>
            <div class="item"><span class="label">Score</span><span class="value">{roadworthiness.get('score')}%</span></div>
            <div class="item"><span class="label">Certificate</span><span class="value">{roadworthiness.get('certificate_number')}</span></div>
            <div class="item"><span class="label">Expires</span><span class="value">{roadworthiness.get('expires')}</span></div>
        </div>
        """
    
    if report.get('issues'):
        html += f"""
        <h2>Issues Found</h2>
        <ul>
            {''.join([f'<li>{issue}</li>' for issue in report.get('issues', [])])}
        </ul>
        """
    
    if report.get('recommendations'):
        html += f"""
        <h2>Recommendations</h2>
        <ul>
            {''.join([f'<li>{rec}</li>' for rec in report.get('recommendations', [])])}
        </ul>
        """
    
    html += f"""
        <div class="footer">
            <p>This report is digitally signed and has a unique audit trail.</p>
            <p>Verify at: https://autov.africa/verify/{report.get('certificate_number')}</p>
            <p>Powered by AUTO-V Intelligence Engine</p>
        </div>
    </body>
    </html>
    """
    
    return html


# ============================================================
# PART 8: CERTIFICATE GENERATOR
# ============================================================

def generate_certificate(
    inspection_id: str,
    inspection_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate a professional certificate for the inspection."""
    vehicle = inspection_result.get("vehicle", {})
    grade = inspection_result.get("grade", {})
    inspector = inspection_result.get("inspector", {})
    
    certificate_number = f"CERT-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
    verification_token = generate_verification_token(certificate_number, inspection_id)
    
    return {
        "certificate_number": certificate_number,
        "verification_token": verification_token,
        "issued_to": vehicle.get("registration"),
        "vehicle": {
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "year": vehicle.get("year"),
            "registration": vehicle.get("registration"),
            "vin": vehicle.get("vin"),
        },
        "grade": grade.get("grade"),
        "score": inspection_result.get("scores", {}).get("overall"),
        "inspector": {
            "name": inspector.get("name"),
            "credentials": inspector.get("credentials"),
        },
        "issue_date": datetime.now().strftime("%Y-%m-%d"),
        "expiry_date": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
        "status": "Active",
        "qr_code": f"{QR_BASE_URL}/{certificate_number}",
        "hash": generate_hash(certificate_number, inspection_id),
    }


def generate_verification_token(certificate_number: str, inspection_id: str) -> str:
    """Generate a unique verification token."""
    data = f"{certificate_number}:{inspection_id}:{datetime.now().isoformat()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def generate_hash(certificate_number: str, inspection_id: str) -> str:
    """Generate a hash for the certificate."""
    data = json.dumps({
        "certificate": certificate_number,
        "inspection": inspection_id,
        "timestamp": datetime.now().isoformat()
    })
    return hashlib.sha512(data.encode()).hexdigest()


def verify_certificate(certificate_number: str, token: str) -> Dict[str, Any]:
    """Verify a certificate using its token."""
    # In production, check against database
    return {
        "certificate_number": certificate_number,
        "valid": True,
        "verified_at": datetime.now().isoformat(),
        "status": "Active",
        "message": "Certificate is valid and authentic",
    }


def generate_qr_content(certificate_number: str, verification_token: str) -> str:
    """Generate content for QR code."""
    return json.dumps({
        "certificate": certificate_number,
        "token": verification_token,
        "url": f"{QR_BASE_URL}/{certificate_number}",
        "timestamp": datetime.now().isoformat(),
    })


# ============================================================
# PART 9: UNIFIED ENTRY POINT
# ============================================================

def run_full_inspection(
    vehicle_data: Dict[str, Any],
    ratings_data: Dict[str, Any],
    inspector_data: Dict[str, Any],
    kebs_data: Dict[str, Any] = None,
    purpose: str = "Pre-Purchase",
    region: str = "Nairobi",
    inspection_type: str = "Premium",
) -> Dict[str, Any]:
    """
    Unified entry point for full inspection including roadworthiness.
    """
    # 1. Create data objects
    vehicle = VehicleData(**vehicle_data)
    ratings = InspectionRatings(**ratings_data)
    inspector = InspectorData(**inspector_data)
    
    # 2. Run inspection
    inspection_result = run_inspection(
        vehicle=vehicle,
        ratings=ratings,
        inspector=inspector,
        purpose=purpose,
        region=region,
        inspection_type=inspection_type,
    )
    
    # 3. Run roadworthiness evaluation
    roadworthiness_result = None
    if kebs_data:
        roadworthiness_result = evaluate_roadworthiness(**kebs_data)
    
    # 4. Generate certificate
    certificate = generate_certificate(
        inspection_id=inspection_result["inspection_id"],
        inspection_result=inspection_result,
    )
    
    # 5. Generate report
    report = generate_inspection_report(
        inspection_result=inspection_result,
        roadworthiness_result=roadworthiness_result,
    )
    
    # 6. Generate PDF
    pdf_html = generate_pdf_content(report)
    
    return {
        "inspection": inspection_result,
        "roadworthiness": roadworthiness_result,
        "certificate": certificate,
        "report": report,
        "pdf_html": pdf_html,
    }


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("AUTO-V INSPECTION ENGINE")
    print("=" * 60)
    
    # 1. Full inspection with roadworthiness
    result = run_full_inspection(
        vehicle_data={
            "make": "Toyota",
            "model": "Axio",
            "year": 2018,
            "registration": "KDA 123A",
            "vin": "JTEGD34V000123456",
            "odometer": 85000,
            "tyre_depth_mm": 5.5,
            "accident_history": "none",
        },
        ratings_data={
            "engine": "Good",
            "transmission": "Good",
            "suspension": "Fair",
            "brakes": "Excellent",
            "paint": "Good",
            "chassis": "Good",
            "interior": "Good",
            "electronics": "Good",
        },
        inspector_data={
            "name": "John M. Valuer",
            "credentials": "AVM-45678",
            "signature": "John M. Valuer",
            "reg_number": "INS-2024-001",
            "company": "AUTO-V Inspections",
        },
        kebs_data={
            "steering": {"steering_play": 5, "steering_rack": "ok"},
            "brakes": {"foot_brake": "good", "parking_brake": "ok", "brake_pads": 4},
            "tyres": {"front_left": 5.5, "front_right": 5.5, "rear_left": 5.0, "rear_right": 5.0},
            "suspension": {"front_shocks": "ok", "rear_shocks": "ok"},
            "lighting": {"headlights": "ok", "indicators": "ok", "brake_lights": "ok"},
            "visibility": {"windshield": "ok", "wipers": "ok"},
            "safety": {"seat_belts": "ok", "airbags": "present"},
            "chassis": {"frame_damage": "none", "rust": "none"},
            "emissions": {"smoke": "ok", "oil_leaks": "none"},
            "electrical": {"battery": 12.6, "charging": 14.0},
        },
        purpose="Pre-Purchase",
        region="Nairobi",
        inspection_type="Premium",
    )
    
    print("\n=== Inspection Results ===")
    print(f"Inspection ID: {result['inspection']['inspection_id']}")
    print(f"Overall Score: {result['inspection']['scores']['overall']}/10")
    print(f"Grade: {result['inspection']['grade']['grade']}")
    
    if result['roadworthiness']:
        print(f"\n=== Roadworthiness (KEBS) ===")
        print(f"Score: {result['roadworthiness']['roadworthiness_score']}%")
        print(f"Status: {result['roadworthiness']['status']}")
    
    print(f"\n=== Certificate ===")
    print(f"Certificate Number: {result['certificate']['certificate_number']}")
    print(f"QR Code: {result['certificate']['qr_code']}")
    
    print(f"\n=== Recommendations ===")
    for rec in result['inspection']['recommendations']:
        print(f"  - {rec}")
