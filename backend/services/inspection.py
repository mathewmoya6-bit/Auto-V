# inspection.py – AUTO-V AI Inspection Engine

import math
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

# Scoring map for condition ratings
SCORE_MAP = {
    "excellent": 10,
    "good": 8,
    "fair": 5,
    "poor": 3,
}

# Weight factors for overall score (safety-critical systems get higher weight)
WEIGHTS = {
    "engine": 0.15,
    "transmission": 0.15,
    "suspension": 0.12,
    "brakes": 0.18,       # Safety critical
    "paint": 0.05,
    "chassis": 0.15,      # Structural integrity
    "interior": 0.05,
    "electronics": 0.10,
    "tyres": 0.05,
}

# Tyre depth scoring (mm)
def tyre_score(depth_mm: float) -> float:
    """
    Convert tyre tread depth (mm) to a score 0-10.
    Legal minimum in Kenya is 1.6mm, but we consider 3mm as threshold.
    """
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

# Accident severity impact on score
ACCIDENT_IMPACT = {
    "none": 0.0,
    "minor": -0.5,
    "moderate": -1.5,
    "major": -3.0,
}

# Generate recommendations based on low scores
def get_recommendations(scores: Dict[str, float]) -> List[str]:
    recommendations = []
    if scores["engine"] < 6:
        recommendations.append("Engine requires professional diagnosis and possible repair.")
    if scores["transmission"] < 6:
        recommendations.append("Transmission may have wear; check fluid levels and shifting quality.")
    if scores["suspension"] < 6:
        recommendations.append("Suspension components may be worn; inspect shocks, bushings, and alignment.")
    if scores["brakes"] < 6:
        recommendations.append("Brake system needs immediate attention; check pads, rotors, and fluid.")
    if scores["chassis"] < 6:
        recommendations.append("Chassis/structural integrity may be compromised; seek professional evaluation.")
    if scores["tyres"] < 4:
        recommendations.append("Tyres are worn below recommended tread depth; replace immediately.")
    if scores["electronics"] < 6:
        recommendations.append("Electrical system has issues; check battery, alternator, and warning lights.")
    return recommendations


def calculate_inspection(
    make: str,
    model: str,
    year: int,
    odometer: int,
    engine_rating: str,           # "Excellent", "Good", "Fair", "Poor"
    transmission_rating: str,
    suspension_rating: str,
    brakes_rating: str,
    paint_rating: str,
    chassis_rating: str,
    interior_rating: str,
    electronics_rating: str,
    tyre_depth_mm: float,
    accident_history: str = "none",   # "none", "minor", "moderate", "major"
    inspector_name: str = "Not specified",
    inspector_credentials: str = "N/A",
    inspection_type: str = "Standard",
    region: str = "Nairobi",
    purpose: str = "pre-purchase",
) -> Dict[str, Any]:
    """
    Perform a professional vehicle inspection and generate a detailed report.

    Args:
        make, model, year, odometer: Basic vehicle info
        engine_rating, transmission_rating, ...: Condition ratings (Excellent, Good, Fair, Poor)
        tyre_depth_mm: Measured tyre tread depth in millimeters
        accident_history: None, Minor, Moderate, Major
        inspector_name: Inspector's full name
        inspector_credentials: License or certification number
        inspection_type: Standard, Premium, Express
        region: Location of inspection
        purpose: Pre-Purchase, Insurance, Fleet, etc.

    Returns:
        Dictionary with inspection results, scores, issues, and recommendations.
    """
    # ---- 1. Convert ratings to numeric scores ----
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

    # ---- 2. Apply accident penalty ----
    accident_penalty = ACCIDENT_IMPACT.get(accident_history.lower(), 0.0)
    # Apply penalty proportionally to all scores except tyres (which are independent)
    for key in scores:
        if key != "tyres":
            scores[key] = max(0, scores[key] + accident_penalty)

    # ---- 3. Calculate weighted overall score ----
    overall = 0.0
    for key, weight in WEIGHTS.items():
        overall += scores[key] * weight
    overall = round(overall, 1)

    # ---- 4. Safety score (focused on brakes, chassis, tyres) ----
    safety = round((scores["brakes"] * 0.4 + scores["chassis"] * 0.3 + scores["tyres"] * 0.3), 1)

    # ---- 5. Mechanical score (engine, transmission, suspension) ----
    mechanical = round((scores["engine"] * 0.4 + scores["transmission"] * 0.3 + scores["suspension"] * 0.3), 1)

    # ---- 6. Issues/Recommendations ----
    issues = get_recommendations(scores)

    # ---- 7. Confidence score ----
    # Based on completeness of data and consistency
    confidence = 100
    # If any rating is missing (should not happen with defaults)
    if any(s == 0 for s in scores.values()):
        confidence -= 10
    if accident_history.lower() == "major":
        confidence -= 15
    if tyre_depth_mm <= 0:
        confidence -= 10
    if inspector_name == "Not specified":
        confidence -= 5
    confidence = max(0, min(100, confidence))

    # ---- 8. Risk score (inverse) ----
    risk_score = 100 - confidence

    # ---- 9. Inspection ID ----
    inspection_id = f"INS-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    # ---- 10. Build result ----
    result = {
        "inspection_id": inspection_id,
        "overall_score": overall,
        "safety_score": safety,
        "mechanical_score": mechanical,
        "scores": scores,
        "accident_penalty": round(accident_penalty, 1),
        "confidence_score": confidence,
        "risk_score": risk_score,
        "issues": issues,
        "recommendations": issues,  # alias
        "inspector": {
            "name": inspector_name,
            "credentials": inspector_credentials,
            "signature": inspector_name,  # digital signature placeholder
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
    }

    return result


def quick_inspection(
    make: str,
    model: str,
    year: int,
    odometer: int,
    condition: str = "good",  # overall shorthand
) -> Dict[str, Any]:
    """
    Fast inspection estimate (used for instant checks or preliminary assessments).
    Returns an overall score and basic details.
    """
    # Map overall condition to ratings for all systems
    rating_map = {
        "excellent": "excellent",
        "good": "good",
        "fair": "fair",
        "poor": "poor",
    }
    rating = rating_map.get(condition.lower(), "good")

    # Assume average tyre depth 6mm
    tyre_depth = 6.0

    result = calculate_inspection(
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
    return result


# -------------------- Example usage --------------------
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
        inspection_type="Premium",
        region="Nairobi",
        purpose="Pre-Purchase",
    )

    print("Inspection Report:")
    print(f"  Overall Score: {inspection['overall_score']}/10")
    print(f"  Safety Score: {inspection['safety_score']}/10")
    print(f"  Mechanical Score: {inspection['mechanical_score']}/10")
    print(f"  Confidence: {inspection['confidence_score']}%")
    print("  Individual Scores:")
    for key, val in inspection["scores"].items():
        print(f"    {key}: {val}/10")
    print("  Issues:")
    for issue in inspection["issues"]:
        print(f"    - {issue}")
    print(f"  Inspector: {inspection['inspector']['name']} ({inspection['inspector']['credentials']})")
    print(f"  Inspection ID: {inspection['inspection_id']}")
