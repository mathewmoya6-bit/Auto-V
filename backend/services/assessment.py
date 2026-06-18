# assessment.py – AUTO-V AI Assessment Engine

import math
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# ---- Assessment type constants ----
ASSESSMENT_TYPES = [
    "accident",
    "insurance_claim",
    "repair_cost",
    "total_loss",
    "salvage",
    "theft_recovery",
]

# ---- Base repair costs by vehicle segment (for repair cost estimation) ----
BASE_REPAIR_COSTS = {
    "small": 150000,
    "compact": 200000,
    "midsize": 280000,
    "large": 400000,
    "suv": 350000,
    "pickup": 300000,
    "van": 320000,
    "luxury": 600000,
}

# Damage severity multipliers
SEVERITY_MULTIPLIERS = {
    "minor": 0.3,
    "moderate": 0.6,
    "major": 0.9,
    "severe": 1.2,
}

# Parts cost factor (relative to base repair)
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
}

# Labour rate per hour (KES)
LABOUR_RATE = 2500

# Salvage value as percentage of pre-accident value
SALVAGE_PERCENTAGE = {
    "minor": 0.85,
    "moderate": 0.65,
    "major": 0.45,
    "severe": 0.25,
}

# Theft recovery condition adjustments
THEFT_RECOVERY_FACTORS = {
    "excellent": 0.95,
    "good": 0.85,
    "fair": 0.70,
    "poor": 0.50,
}

# Loss threshold for total loss determination (repair cost / market value)
TOTAL_LOSS_THRESHOLD = 0.65

def get_segment(make: str, model: str) -> str:
    """
    Determine vehicle segment based on make and model.
    Simplified: returns segment based on known models.
    """
    make_lower = make.lower()
    model_lower = model.lower()

    # Luxury brands
    luxury_brands = ["mercedes", "bmw", "audi", "lexus", "jaguar", "land rover", "porsche"]
    if any(b in make_lower for b in luxury_brands):
        return "luxury"

    # SUVs
    suv_models = ["rav4", "cr-v", "x-trail", "forester", "outlander", "tucson", "sportage", "cx-5"]
    if any(m in model_lower for m in suv_models) or "suv" in model_lower:
        return "suv"

    # Pickups
    pickup_models = ["hilux", "ranger", "d-max", "navara", "triton"]
    if any(m in model_lower for m in pickup_models):
        return "pickup"

    # Vans
    van_models = ["hiace", "transit", "delica", "nv200"]
    if any(m in model_lower for m in van_models):
        return "van"

    # Large sedans
    large_models = ["camry", "accord", "legacy", "mazda6", "passat", "superb"]
    if any(m in model_lower for m in large_models):
        return "large"

    # Midsize
    midsize_models = ["corolla", "civic", "axio", "premio", "allion", "elantra", "cerato", "3"]
    if any(m in model_lower for m in midsize_models):
        return "midsize"

    # Compact
    compact_models = ["vitz", "fit", "note", "swift", "rio", "i20", "polo", "208"]
    if any(m in model_lower for m in compact_models):
        return "compact"

    # Small
    small_models = ["passo", "demio", "picanto", "i10", "ignis"]
    if any(m in model_lower for m in small_models):
        return "small"

    # Default
    return "compact"


def estimate_repair_cost(
    segment: str,
    damage_severity: str,
    parts_affected: List[str],
    labour_hours: float = 8.0,
) -> Dict[str, float]:
    """
    Estimate repair cost based on vehicle segment, severity, affected parts, and labour.

    Returns:
        Dictionary with 'parts_cost', 'labour_cost', 'total_cost', 'parts_breakdown'
    """
    base = BASE_REPAIR_COSTS.get(segment, 200000)
    severity_mult = SEVERITY_MULTIPLIERS.get(damage_severity, 0.5)

    parts_cost = 0.0
    parts_breakdown = {}

    # Each part contributes to the repair
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
    }


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
    segment = get_segment(make, model)
    repair_est = estimate_repair_cost(segment, damage_severity, parts_affected)

    # Determine if the vehicle is likely a total loss
    repair_ratio = repair_est["total_cost"] / max(market_value, 1)
    total_loss = repair_ratio >= TOTAL_LOSS_THRESHOLD

    # Confidence based on data completeness
    confidence = 100
    if not police_report:
        confidence -= 10
    if not description:
        confidence -= 5
    if damage_severity in ["severe", "major"] and not police_report:
        confidence -= 15
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
) -> Dict[str, Any]:
    """
    Insurance claim assessment for processing.

    Returns:
        Assessment report suitable for insurance claims processing.
    """
    segment = get_segment(make, model)
    repair_est = estimate_repair_cost(segment, damage_severity, parts_affected)

    # Claim assessment: decide if the claim is valid and estimate payout
    payout_ratio = 0.85  # Insurance typically pays 85% of repair cost after excess
    estimated_payout = repair_est["total_cost"] * payout_ratio
    estimated_payout = math.ceil(estimated_payout / 100) * 100

    # Check if claim exceeds vehicle value (total loss)
    loss_ratio = repair_est["total_cost"] / max(market_value, 1)
    total_loss = loss_ratio >= TOTAL_LOSS_THRESHOLD

    assessment_id = f"CLM-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    result = {
        "assessment_id": assessment_id,
        "type": "insurance_claim",
        "claim": {
            "number": claim_number,
            "company": insurance_company,
            "adjuster": adjuster_name,
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
) -> Dict[str, Any]:
    """
    Standalone repair cost assessment (without incident details).
    Useful for pre-purchase or pre-repair quotes.
    """
    segment = get_segment(make, model)
    repair_est = estimate_repair_cost(segment, damage_severity, parts_affected)

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
) -> Dict[str, Any]:
    """
    Determine if a vehicle should be declared a total loss.
    """
    loss_ratio = repair_estimate / max(market_value, 1)
    total_loss = loss_ratio >= TOTAL_LOSS_THRESHOLD

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
        "loss_ratio": round(loss_ratio, 2),
        "total_loss": total_loss,
        "threshold": TOTAL_LOSS_THRESHOLD,
        "policy_details": insurance_policy_details,
        "recommendation": "Declare Total Loss" if total_loss else "Repair Recommended",
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
    heavy_parts = ["engine", "transmission", "chassis"]
    if any(p in heavy_parts for p in parts_affected):
        salvage_value *= 0.80  # Further reduction
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
            "police_station": police_station,
        },
        "condition": {
            "rating": condition,
            "factor": condition_factor,
            "modifications": modifications,
        },
        "value_loss": market_value - recovered_value,
        "loss_percentage": round((1 - condition_factor) * 100, 1),
        "generated_at": datetime.now().isoformat(),
    }
    return result


# -------------------- Helper: Quick assessment router --------------------
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


# -------------------- Example usage --------------------
if __name__ == "__main__":
    # 1. Accident Assessment
    print("=== Accident Assessment ===")
    accident_result = assess_accident(
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
    print(f"Repair Cost: KES {accident_result['repair_estimate']['total_cost']:,}")
    print(f"Total Loss: {accident_result['total_loss']}")

    # 2. Insurance Claim Assessment
    print("\n=== Insurance Claim Assessment ===")
    claim_result = assess_insurance_claim(
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
    print(f"Estimated Payout: KES {claim_result['estimated_payout']:,}")

    # 3. Repair Cost Assessment
    print("\n=== Repair Cost Assessment ===")
    repair_result = assess_repair_cost(
        make="Subaru",
        model="Forester",
        year=2017,
        damage_severity="moderate",
        parts_affected=["engine", "transmission", "suspension"],
        market_value=2800000,
    )
    print(f"Repair Cost: KES {repair_result['repair_estimate']['total_cost']:,}")

    # 4. Total Loss Assessment
    print("\n=== Total Loss Assessment ===")
    total_loss_result = assess_total_loss(
        make="Nissan",
        model="X-Trail",
        year=2016,
        market_value=2500000,
        repair_estimate=1800000,
        insurance_policy_details="Comprehensive with KES 50,000 excess"
    )
    print(f"Total Loss: {total_loss_result['total_loss']}")

    # 5. Salvage Assessment
    print("\n=== Salvage Assessment ===")
    salvage_result = assess_salvage(
        make="Mercedes",
        model="C-Class",
        year=2019,
        pre_accident_value=4500000,
        damage_severity="major",
        parts_affected=["engine", "body", "chassis"]
    )
    print(f"Salvage Value: KES {salvage_result['salvage_value']:,}")

    # 6. Theft Recovery Assessment
    print("\n=== Theft Recovery Assessment ===")
    theft_result = assess_theft_recovery(
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
    print(f"Recovered Value: KES {theft_result['vehicle']['recovered_value']:,}")
    print(f"Value Loss: KES {theft_result['value_loss']:,}")
