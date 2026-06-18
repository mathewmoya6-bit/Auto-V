# assessment.py – AUTO-V AI Assessment Engine (Production-Ready)

import math
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# ============================================================
# ASSESSMENT TYPES
# ============================================================
ASSESSMENT_TYPES = [
    "accident",
    "insurance_claim",
    "repair_cost",
    "total_loss",
    "salvage",
    "theft_recovery"
]

# ============================================================
# BASE REPAIR COSTS BY VEHICLE SEGMENT
# ============================================================
BASE_REPAIR_COSTS = {
    "small": 150000,
    "compact": 200000,
    "midsize": 280000,
    "large": 400000,
    "suv": 350000,
    "pickup": 300000,
    "van": 320000,
    "luxury": 600000,
    "minibus": 450000,
    "bus": 700000,
    "motorcycle": 80000,
}

# Damage severity multipliers
SEVERITY_MULTIPLIERS = {
    "minor": 0.25,
    "moderate": 0.55,
    "major": 0.85,
    "severe": 1.20,
    "catastrophic": 1.50,
}

# Parts cost factors
PARTS_FACTOR = {
    "engine": 0.40,
    "transmission": 0.30,
    "suspension": 0.15,
    "brakes": 0.10,
    "body": 0.25,
    "paint": 0.08,
    "electrical": 0.12,
    "interior": 0.10,
    "chassis": 0.35,
    "tyres": 0.05,
    "airbags": 0.15,
    "cooling": 0.08,
    "exhaust": 0.06,
    "fuel_system": 0.12,
    "steering": 0.14,
}

# Labour rate per hour (KES)
LABOUR_RATE = 2500

# Salvage value as percentage of pre-accident value
SALVAGE_PERCENTAGE = {
    "minor": 0.85,
    "moderate": 0.65,
    "major": 0.45,
    "severe": 0.25,
    "catastrophic": 0.10,
}

# Theft recovery condition adjustments
THEFT_RECOVERY_FACTORS = {
    "excellent": 0.95,
    "good": 0.85,
    "fair": 0.70,
    "poor": 0.50,
    "damaged": 0.35,
}

# Total loss threshold (repair cost / market value)
TOTAL_LOSS_THRESHOLD = 0.65

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_vehicle_segment(make: str, model: str) -> str:
    """
    Determine vehicle segment based on make and model.
    """
    make_lower = make.lower()
    model_lower = model.lower()

    # Luxury brands
    luxury_brands = ["mercedes", "bmw", "audi", "lexus", "jaguar", "land rover", "porsche", "bentley", "rolls royce"]
    if any(b in make_lower for b in luxury_brands):
        return "luxury"

    # SUVs
    suv_models = ["rav4", "cr-v", "x-trail", "forester", "outlander", "tucson", "sportage", "cx-5", "qashqai", "kuga", "escape"]
    if any(m in model_lower for m in suv_models) or "suv" in model_lower:
        return "suv"

    # Pickups
    pickup_models = ["hilux", "ranger", "d-max", "navara", "triton", "amarok", "tacoma", "f-150"]
    if any(m in model_lower for m in pickup_models):
        return "pickup"

    # Vans & Minibuses
    van_models = ["hiace", "transit", "delica", "nv200", "probox", "urban", "minibus"]
    if any(m in model_lower for m in van_models):
        return "van"
    
    # Buses
    bus_models = ["coaster", "isuzu bus", "scania", "mercedes bus"]
    if any(m in model_lower for m in bus_models) or "bus" in model_lower:
        return "bus"

    # Motorcycles
    motorcycle_models = ["boxer", "star", "tv", "honda bike", "yamaha", "suzuki bike"]
    if any(m in model_lower for m in motorcycle_models) or "motorcycle" in model_lower or "bike" in model_lower:
        return "motorcycle"

    # Large sedans
    large_models = ["camry", "accord", "legacy", "mazda6", "passat", "superb", "avalon", "crown"]
    if any(m in model_lower for m in large_models):
        return "large"

    # Midsize sedans
    midsize_models = ["corolla", "civic", "axio", "premio", "allion", "elantra", "cerato", "mazda3"]
    if any(m in model_lower for m in midsize_models):
        return "midsize"

    # Compact cars
    compact_models = ["vitz", "fit", "note", "swift", "rio", "i20", "polo", "208", "fiesta", "micra"]
    if any(m in model_lower for m in compact_models):
        return "compact"

    # Small cars
    small_models = ["passo", "demio", "picanto", "i10", "ignis", "alto", "morning", "spark"]
    if any(m in model_lower for m in small_models):
        return "small"

    # Default
    return "compact"


def estimate_repair_cost(
    segment: str,
    damage_severity: str,
    parts_affected: List[str],
    labour_hours: float = 8.0,
) -> Dict[str, Any]:
    """
    Estimate repair cost based on vehicle segment, severity, and affected parts.
    
    Returns:
        Dict with 'parts_cost', 'labour_cost', 'total_cost', 'parts_breakdown'
    """
    base = BASE_REPAIR_COSTS.get(segment, 200000)
    severity_mult = SEVERITY_MULTIPLIERS.get(damage_severity, 0.5)

    parts_cost = 0.0
    parts_breakdown = {}

    # Each affected part contributes to the repair
    for part in parts_affected:
        part_factor = PARTS_FACTOR.get(part, 0.10)
        part_cost = base * part_factor * severity_mult
        parts_cost += part_cost
        parts_breakdown[part] = round(part_cost, 2)

    # Labour cost
    labour_cost = labour_hours * LABOUR_RATE

    total_cost = parts_cost + labour_cost

    # Round to nearest 100
    total_cost = math.ceil(total_cost / 100) * 100
    parts_cost = math.ceil(parts_cost / 100) * 100
    labour_cost = math.ceil(labour_cost / 100) * 100

    return {
        "parts_cost": parts_cost,
        "labour_cost": labour_cost,
        "total_cost": total_cost,
        "parts_breakdown": parts_breakdown,
        "labour_hours": labour_hours,
        "base_repair_cost": base,
        "severity_multiplier": severity_mult,
    }


def calculate_confidence_score(data_completeness: float, data_quality: float) -> int:
    """Calculate confidence score based on data completeness and quality."""
    score = 70  # Base score
    score += data_completeness * 0.25
    score += data_quality * 0.15
    return min(100, max(0, round(score)))


# ============================================================
# ASSESSMENT FUNCTIONS
# ============================================================

def assess_accident(
    make: str,
    model: str,
    year: int,
    market_value: int,
    damage_severity: str,
    parts_affected: List[str],
    incident_date: str,
    location: str = "Nairobi",
    police_report: Optional[str] = None,
    description: str = "",
) -> Dict[str, Any]:
    """
    Perform accident assessment.
    
    Returns:
        Assessment report with repair cost, severity, and recommendations.
    """
    segment = get_vehicle_segment(make, model)
    repair_est = estimate_repair_cost(segment, damage_severity, parts_affected)

    # Determine if total loss
    repair_ratio = repair_est["total_cost"] / max(market_value, 1)
    total_loss = repair_ratio >= TOTAL_LOSS_THRESHOLD

    # Confidence based on data completeness
    confidence = 100
    if not police_report:
        confidence -= 10
    if not description:
        confidence -= 5
    if damage_severity in ["severe", "catastrophic"] and not police_report:
        confidence -= 15
    if not parts_affected:
        confidence -= 10
    confidence = max(0, min(100, confidence))

    assessment_id = f"ACC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    result = {
        "assessment_id": assessment_id,
        "type": "accident",
        "vehicle": {
            "make": make,
            "model": model,
            "year": year,
            "market_value": market_value,
        },
        "incident": {
            "date": incident_date,
            "location": location,
            "severity": damage_severity,
            "police_report": police_report,
            "description": description,
        },
        "repair_estimate": repair_est,
        "total_loss": total_loss,
        "repair_ratio": round(repair_ratio, 2),
        "confidence_score": confidence,
        "recommendation": "Total Loss" if total_loss else "Repairable",
        "generated_at": datetime.now().isoformat(),
    }
    return result


def assess_insurance_claim(
    make: str,
    model: str,
    year: int,
    market_value: int,
    claim_number: str,
    insurance_company: str,
    damage_severity: str,
    parts_affected: List[str],
    adjuster_name: Optional[str] = None,
    policy_excess: int = 5000,
) -> Dict[str, Any]:
    """
    Insurance claim assessment for processing.
    
    Returns:
        Assessment report suitable for insurance claims processing.
    """
    segment = get_vehicle_segment(make, model)
    repair_est = estimate_repair_cost(segment, damage_severity, parts_affected)

    # Claim assessment: calculate payout
    payout_ratio = 0.85  # Insurance typically pays 85% of repair cost after excess
    estimated_payout = repair_est["total_cost"] * payout_ratio - policy_excess
    estimated_payout = max(0, math.ceil(estimated_payout / 100) * 100)

    # Check if claim exceeds vehicle value (total loss)
    loss_ratio = repair_est["total_cost"] / max(market_value, 1)
    total_loss = loss_ratio >= TOTAL_LOSS_THRESHOLD

    assessment_id = f"CLM-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    # Determine if claim is valid
    claim_valid = True
    validation_notes = []
    if loss_ratio > 0.9:
        claim_valid = False
        validation_notes.append("Claim exceeds 90% of vehicle value - consider total loss")
    if repair_est["total_cost"] < 1000:
        claim_valid = False
        validation_notes.append("Repair cost is below minimum threshold")

    result = {
        "assessment_id": assessment_id,
        "type": "insurance_claim",
        "claim": {
            "number": claim_number,
            "company": insurance_company,
            "adjuster": adjuster_name,
            "policy_excess": policy_excess,
        },
        "vehicle": {
            "make": make,
            "model": model,
            "year": year,
            "market_value": market_value,
        },
        "repair_estimate": repair_est,
        "estimated_payout": estimated_payout,
        "payout_ratio": payout_ratio,
        "total_loss": total_loss,
        "loss_ratio": round(loss_ratio, 2),
        "claim_valid": claim_valid,
        "validation_notes": validation_notes,
        "recommendation": "Total Loss" if total_loss else "Repair Approved",
        "generated_at": datetime.now().isoformat(),
    }
    return result


def assess_repair_cost(
    make: str,
    model: str,
    year: int,
    damage_severity: str,
    parts_affected: List[str],
    market_value: Optional[int] = None,
    labour_hours: float = 8.0,
) -> Dict[str, Any]:
    """
    Standalone repair cost assessment (without incident details).
    Useful for pre-purchase or pre-repair quotes.
    """
    segment = get_vehicle_segment(make, model)
    repair_est = estimate_repair_cost(segment, damage_severity, parts_affected, labour_hours)

    assessment_id = f"RPR-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    result = {
        "assessment_id": assessment_id,
        "type": "repair_cost",
        "vehicle": {
            "make": make,
            "model": model,
            "year": year,
        },
        "damage": {
            "severity": damage_severity,
            "parts_affected": parts_affected,
        },
        "repair_estimate": repair_est,
        "generated_at": datetime.now().isoformat(),
    }
    if market_value:
        result["market_value"] = market_value
        result["repair_ratio"] = round(repair_est["total_cost"] / max(market_value, 1), 2)
        result["total_loss"] = result["repair_ratio"] >= TOTAL_LOSS_THRESHOLD
    return result


def assess_total_loss(
    make: str,
    model: str,
    year: int,
    market_value: int,
    repair_estimate: int,
    insurance_policy_details: str = "",
    salvage_value: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Determine if a vehicle should be declared a total loss.
    """
    loss_ratio = repair_estimate / max(market_value, 1)
    total_loss = loss_ratio >= TOTAL_LOSS_THRESHOLD
    
    # Calculate salvage value if not provided
    if salvage_value is None:
        salvage_value = int(market_value * 0.25)

    assessment_id = f"TL-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    result = {
        "assessment_id": assessment_id,
        "type": "total_loss",
        "vehicle": {
            "make": make,
            "model": model,
            "year": year,
            "market_value": market_value,
        },
        "repair_estimate": repair_estimate,
        "salvage_value": salvage_value,
        "loss_ratio": round(loss_ratio, 2),
        "total_loss": total_loss,
        "threshold": TOTAL_LOSS_THRESHOLD,
        "policy_details": insurance_policy_details,
        "recommendation": "Declare Total Loss" if total_loss else "Repair Recommended",
        "financial_impact": {
            "vehicle_value": market_value,
            "repair_cost": repair_estimate,
            "salvage_value": salvage_value,
            "net_loss": market_value - salvage_value if total_loss else repair_estimate,
        },
        "generated_at": datetime.now().isoformat(),
    }
    return result


def assess_salvage(
    make: str,
    model: str,
    year: int,
    pre_accident_value: int,
    damage_severity: str,
    parts_affected: List[str],
) -> Dict[str, Any]:
    """
    Determine salvage value of a damaged vehicle.
    """
    salvage_percent = SALVAGE_PERCENTAGE.get(damage_severity, 0.65)
    salvage_value = pre_accident_value * salvage_percent
    salvage_value = math.ceil(salvage_value / 100) * 100

    # Adjust salvage value based on parts affected
    # Certain parts reduce salvage value more
    heavy_parts = ["engine", "transmission", "chassis", "body"]
    if any(p in heavy_parts for p in parts_affected):
        salvage_value *= 0.80
        salvage_value = math.ceil(salvage_value / 100) * 100

    assessment_id = f"SLV-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    result = {
        "assessment_id": assessment_id,
        "type": "salvage",
        "vehicle": {
            "make": make,
            "model": model,
            "year": year,
            "pre_accident_value": pre_accident_value,
        },
        "damage": {
            "severity": damage_severity,
            "parts_affected": parts_affected,
        },
        "salvage_value": salvage_value,
        "salvage_percentage": salvage_percent,
        "valuation_recommendation": f"Salvage value estimated at {salvage_value:,} KES",
        "generated_at": datetime.now().isoformat(),
    }
    return result


def assess_theft_recovery(
    make: str,
    model: str,
    year: int,
    odometer: int,
    condition: str,
    theft_date: str,
    recovery_date: str,
    police_station: str,
    market_value: int,
    modifications: str = "none",
) -> Dict[str, Any]:
    """
    Assess a recovered stolen vehicle for value and condition.
    """
    # Adjust market value based on recovery condition
    condition_factor = THEFT_RECOVERY_FACTORS.get(condition.lower(), 0.85)
    recovered_value = market_value * condition_factor
    recovered_value = math.ceil(recovered_value / 100) * 100

    # Apply odometer wear adjustment (if high mileage)
    wear_factor = max(0.7, 1 - (odometer / 300000))
    recovered_value *= wear_factor
    recovered_value = math.ceil(recovered_value / 100) * 100

    # Calculate time between theft and recovery (in days)
    theft_date_obj = datetime.strptime(theft_date, "%Y-%m-%d")
    recovery_date_obj = datetime.strptime(recovery_date, "%Y-%m-%d")
    days_missing = (recovery_date_obj - theft_date_obj).days

    # Additional depreciation for days missing
    days_factor = max(0.85, 1 - (days_missing / 365) * 0.05)
    recovered_value *= days_factor
    recovered_value = math.ceil(recovered_value / 100) * 100

    assessment_id = f"THF-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    result = {
        "assessment_id": assessment_id,
        "type": "theft_recovery",
        "vehicle": {
            "make": make,
            "model": model,
            "year": year,
            "odometer": odometer,
            "market_value": market_value,
            "recovered_value": recovered_value,
        },
        "theft": {
            "theft_date": theft_date,
            "recovery_date": recovery_date,
            "days_missing": days_missing,
            "police_station": police_station,
        },
        "condition": {
            "rating": condition,
            "factor": condition_factor,
            "modifications": modifications,
        },
        "value_loss": market_value - recovered_value,
        "loss_percentage": round((1 - (recovered_value / market_value)) * 100, 1),
        "recommendation": "Recovered - Value Reduced" if recovered_value < market_value * 0.7 else "Good Recovery Condition",
        "generated_at": datetime.now().isoformat(),
    }
    return result


# ============================================================
# UNIFIED ENTRY POINT
# ============================================================

def assess(
    assessment_type: str,
    **kwargs,
) -> Dict[str, Any]:
    """
    Unified entry point for all assessment types.

    Usage:
        result = assess(
            "accident",
            make="Toyota",
            model="Axio",
            year=2018,
            market_value=2000000,
            damage_severity="moderate",
            parts_affected=["body", "paint", "suspension"],
            incident_date="2025-01-15"
        )
    """
    if assessment_type not in ASSESSMENT_TYPES:
        raise ValueError(f"Unsupported assessment type: {assessment_type}. Choose from {ASSESSMENT_TYPES}")

    function_map = {
        "accident": assess_accident,
        "insurance_claim": assess_insurance_claim,
        "repair_cost": assess_repair_cost,
        "total_loss": assess_total_loss,
        "salvage": assess_salvage,
        "theft_recovery": assess_theft_recovery,
    }
    func = function_map[assessment_type]
    return func(**kwargs)


# ============================================================
# EXAMPLE USAGE
# ============================================================
if __name__ == "__main__":
    # Test all assessment types
    print("=== Accident Assessment ===")
    result = assess_accident(
        make="Toyota",
        model="Axio",
        year=2018,
        market_value=2000000,
        damage_severity="moderate",
        parts_affected=["body", "paint", "suspension"],
        incident_date="2025-01-15",
        location="Nairobi",
        police_report="POL-2025-001234",
        description="Side impact collision at low speed."
    )
    print(f"Repair Cost: KES {result['repair_estimate']['total_cost']:,}")
    print(f"Total Loss: {result['total_loss']}")
    print(f"Confidence: {result['confidence_score']}%\n")

    print("=== Insurance Claim Assessment ===")
    result = assess_insurance_claim(
        make="Honda",
        model="CR-V",
        year=2019,
        market_value=3200000,
        claim_number="CLM-2025-5678",
        insurance_company="Britam",
        damage_severity="minor",
        parts_affected=["body", "paint"],
        adjuster_name="Jane M."
    )
    print(f"Estimated Payout: KES {result['estimated_payout']:,}")
    print(f"Claim Valid: {result['claim_valid']}\n")

    print("=== Repair Cost Assessment ===")
    result = assess_repair_cost(
        make="Subaru",
        model="Forester",
        year=2017,
        damage_severity="moderate",
        parts_affected=["engine", "transmission", "suspension"],
        market_value=2800000,
        labour_hours=12
    )
    print(f"Repair Cost: KES {result['repair_estimate']['total_cost']:,}")
    print(f"Repair Ratio: {result['repair_ratio']}\n")

    print("=== Total Loss Assessment ===")
    result = assess_total_loss(
        make="Nissan",
        model="X-Trail",
        year=2016,
        market_value=2500000,
        repair_estimate=1800000,
        insurance_policy_details="Comprehensive with KES 50,000 excess"
    )
    print(f"Total Loss: {result['total_loss']}\n")

    print("=== Salvage Assessment ===")
    result = assess_salvage(
        make="Mercedes",
        model="C-Class",
        year=2019,
        pre_accident_value=4500000,
        damage_severity="major",
        parts_affected=["engine", "body", "chassis"]
    )
    print(f"Salvage Value: KES {result['salvage_value']:,}\n")

    print("=== Theft Recovery Assessment ===")
    result = assess_theft_recovery(
        make="Toyota",
        model="Prado",
        year=2020,
        odometer=60000,
        condition="fair",
        theft_date="2024-12-01",
        recovery_date="2025-01-20",
        police_station="Nairobi Central",
        market_value=8000000,
        modifications="none"
    )
    print(f"Recovered Value: KES {result['vehicle']['recovered_value']:,}")
    print(f"Value Loss: KES {result['value_loss']:,}")
