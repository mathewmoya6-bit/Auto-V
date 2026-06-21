# services/inspection.py – AUTO-V AI Inspection Engine
# Production-Ready - Aligned with Frontend and API Routes

import math
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# ─── SCORING MAP ──────────────────────────────────────────────────

SCORE_MAP = {
    "excellent": 10,
    "good": 8,
    "fair": 5,
    "poor": 3,
}

# ─── WEIGHT FACTORS ─────────────────────────────────────────────

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

# ─── TYRE DEPTH SCORING ─────────────────────────────────────────

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

# ─── ACCIDENT IMPACT ─────────────────────────────────────────────

ACCIDENT_IMPACT = {
    "none": 0.0,
    "minor": -0.5,
    "moderate": -1.5,
    "major": -3.0,
}

# ─── INSPECTION PRICING ─────────────────────────────────────────

INSPECTION_PRICES = {
    "Pre-Purchase": 3500,
    "Insurance": 4000,
    "Loan/Finance": 4500,
    "Fleet": 5000,
    "Export": 6000,
    "Other": 3500,
}

# ─── GENERATE RECOMMENDATIONS ───────────────────────────────────

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


# ─── CORE INSPECTION FUNCTION ───────────────────────────────────

def calculate_inspection(
    make: str,
    model: str,
    year: int,
    odometer: int,
    engine_rating: str,
    transmission_rating: str,
    suspension_rating: str,
    brakes_rating: str,
    paint_rating: str,
    chassis_rating: str,
    interior_rating: str,
    electronics_rating: str,
    tyre_depth_mm: float,
    accident_history: str = "none",
    inspector_name: str = "Not specified",
    inspector_credentials: str = "N/A",
    inspector_signature: str = "",
    inspection_type: str = "Premium",
    region: str = "Nairobi",
    purpose: str = "Pre-Purchase",
    inspector: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Perform a professional vehicle inspection and generate a detailed report.
    Aligned with frontend inspection engine.
    """
    # ─── 1. Convert ratings to numeric scores ──────────────────
    scores = {
        "engine": SCORE_MAP.get(engine_rating.lower(), 5),
        "transmission": SCORE_MAP.get(transmission_rating.lower(), 5),
        "suspension": SCORE_MAP.get(suspension_rating.lower(), 5),
        "brakes": SCORE_MAP.get(brakes_rating.lower(), 5),
        "paint": SCORE_MAP.get(paint_rating.lower(), 5),
        "chassis": SCORE_MAP.get(chassis_rating.lower(), 5),
        "interior": SCORE_MAP.get(interior_rating.lower(), 5),
        "electronics": SCORE_MAP.get(electronics_rating.lower(), 5),
        "tyres": tyre_score(tyre_depth_mm),
    }

    # ─── 2. Apply accident penalty ─────────────────────────────
    accident_penalty = ACCIDENT_IMPACT.get(accident_history.lower(), 0.0)
    for key in scores:
        if key != "tyres":
            scores[key] = max(0, scores[key] + accident_penalty)

    # ─── 3. Calculate weighted overall score ───────────────────
    overall = 0.0
    for key, weight in WEIGHTS.items():
        overall += scores[key] * weight
    overall = round(overall, 1)

    # ─── 4. Category scores ────────────────────────────────────
    exterior = round((scores["paint"] + scores["chassis"] + (10 + accident_penalty if accident_penalty < 0 else 10)) / 3, 1)
    interior = scores["interior"]
    mechanical = round((scores["engine"] + scores["transmission"] + scores["suspension"]) / 3, 1)
    electrical = scores["electronics"]
    safety = round((scores["brakes"] * 0.4 + scores["chassis"] * 0.3 + scores["tyres"] * 0.3), 1)

    # ─── 5. Issues/Recommendations ─────────────────────────────
    issues = get_recommendations(scores)

    # ─── 6. Confidence score ───────────────────────────────────
    confidence = 100
    if any(s == 0 for s in scores.values()):
        confidence -= 10
    if accident_history.lower() == "major":
        confidence -= 15
    elif accident_history.lower() == "moderate":
        confidence -= 10
    if tyre_depth_mm <= 0:
        confidence -= 10
    if inspector_name == "Not specified":
        confidence -= 5
    if not inspector_signature:
        confidence -= 5
    confidence = max(0, min(100, confidence))

    # ─── 7. Risk score ─────────────────────────────────────────
    risk_score = 100 - confidence

    # ─── 8. Inspection ID ──────────────────────────────────────
    inspection_id = f"INS-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    # ─── 9. Get inspector data ─────────────────────────────────
    if inspector:
        inspector_name = inspector.get('name', inspector_name)
        inspector_credentials = inspector.get('credentials', inspector_credentials)
        inspector_signature = inspector.get('signature', inspector_signature)

    # ─── 10. Build result ──────────────────────────────────────
    result = {
        "inspection_id": inspection_id,
        "overall_score": overall,
        "exterior_score": exterior,
        "interior_score": interior,
        "mechanical_score": mechanical,
        "electrical_score": electrical,
        "safety_score": safety,
        "scores": scores,
        "accident_penalty": round(accident_penalty, 1),
        "confidence_score": confidence,
        "risk_score": risk_score,
        "issues": issues,
        "recommendations": issues,
        "inspector": {
            "name": inspector_name,
            "credentials": inspector_credentials,
            "signature": inspector_signature or inspector_name,
        },
        "vehicle": {
            "make": make,
            "model": model,
            "year": year,
            "odometer": odometer,
            "tyre_depth_mm": tyre_depth_mm,
            "accident_history": accident_history,
        },
        "inspection_details": {
            "type": inspection_type,
            "region": region,
            "purpose": purpose,
            "date": datetime.now().strftime("%Y-%m-%d"),
        },
        "generated_at": datetime.now().isoformat(),
        "certificate_number": f"INS-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
    }

    return result


# ─── QUICK INSPECTION ───────────────────────────────────────────

def quick_inspection(
    make: str,
    model: str,
    year: int,
    odometer: int,
    condition: str = "good",
) -> Dict[str, Any]:
    """Fast inspection estimate for instant checks."""
    rating_map = {"excellent": "excellent", "good": "good", "fair": "fair", "poor": "poor"}
    rating = rating_map.get(condition.lower(), "good")
    tyre_depth = 6.0

    return calculate_inspection(
        make=make,
        model=model,
        year=year,
        odometer=odometer,
        engine_rating=rating,
        transmission_rating=rating,
        suspension_rating=rating,
        brakes_rating=rating,
        paint_rating=rating,
        chassis_rating=rating,
        interior_rating=rating,
        electronics_rating=rating,
        tyre_depth_mm=tyre_depth,
        accident_history="none",
        inspector_name="Automated",
        inspector_credentials="AI-ESTIMATE",
        inspection_type="Express",
        region="Nairobi",
        purpose="quick_estimate",
    )


# ─── GET INSPECTION PRICE ──────────────────────────────────────

def get_inspection_price(purpose: str) -> int:
    """Get the price for a specific inspection purpose."""
    return INSPECTION_PRICES.get(purpose, 3500)


# ─── VALIDATE INSPECTION DATA ──────────────────────────────────

def validate_inspection_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate inspection input data."""
    required_fields = ['make', 'model', 'year']
    
    for field in required_fields:
        if not data.get(field):
            return False, f"Missing required field: {field}"
    
    if not str(data.get('year', '')).isdigit():
        return False, "Year must be a valid number"
    
    return True, None


# ─── UNIFIED ENTRY POINT ───────────────────────────────────────

def run_inspection(
    make: str,
    model: str,
    year: int,
    odometer: int = 0,
    engine_rating: str = "Good",
    transmission_rating: str = "Good",
    suspension_rating: str = "Good",
    brakes_rating: str = "Good",
    paint_rating: str = "Good",
    chassis_rating: str = "Good",
    interior_rating: str = "Good",
    electronics_rating: str = "Good",
    tyre_depth_mm: float = 6.0,
    accident_history: str = "none",
    inspector_name: str = "Not specified",
    inspector_credentials: str = "N/A",
    inspector_signature: str = "",
    inspection_type: str = "Premium",
    region: str = "Nairobi",
    purpose: str = "Pre-Purchase",
    inspector: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Unified entry point for inspection."""
    return calculate_inspection(
        make=make,
        model=model,
        year=year,
        odometer=odometer,
        engine_rating=engine_rating,
        transmission_rating=transmission_rating,
        suspension_rating=suspension_rating,
        brakes_rating=brakes_rating,
        paint_rating=paint_rating,
        chassis_rating=chassis_rating,
        interior_rating=interior_rating,
        electronics_rating=electronics_rating,
        tyre_depth_mm=tyre_depth_mm,
        accident_history=accident_history,
        inspector_name=inspector_name,
        inspector_credentials=inspector_credentials,
        inspector_signature=inspector_signature,
        inspection_type=inspection_type,
        region=region,
        purpose=purpose,
        inspector=inspector,
    )


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    # Full inspection
    inspection = calculate_inspection(
        make="Toyota",
        model="Axio",
        year=2018,
        odometer=85000,
        engine_rating="Good",
        transmission_rating="Good",
        suspension_rating="Fair",
        brakes_rating="Excellent",
        paint_rating="Good",
        chassis_rating="Good",
        interior_rating="Good",
        electronics_rating="Good",
        tyre_depth_mm=5.5,
        accident_history="None",
        inspector_name="John M. Valuer",
        inspector_credentials="AVM-45678",
        inspector_signature="John M. Valuer",
        inspection_type="Premium",
        region="Nairobi",
        purpose="Pre-Purchase",
    )

    print("=" * 60)
    print("INSPECTION REPORT")
    print("=" * 60)
    print(f"Inspection ID: {inspection['inspection_id']}")
    print(f"Overall Score: {inspection['overall_score']}/10")
    print(f"Safety Score: {inspection['safety_score']}/10")
    print(f"Mechanical Score: {inspection['mechanical_score']}/10")
    print(f"Confidence: {inspection['confidence_score']}%")
    print("\nIndividual Scores:")
    for key, val in inspection['scores'].items():
        print(f"  {key}: {val}/10")
    print("\nIssues:")
    for issue in inspection['issues']:
        print(f"  - {issue}")
    print(f"\nInspector: {inspection['inspector']['name']} ({inspection['inspector']['credentials']})")
    print(f"Certificate: {inspection['certificate_number']}")
