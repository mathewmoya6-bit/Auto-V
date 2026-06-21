# services/assessment.py – AUTO-V AI Assessment Engine
# Production-Ready - Aligned with api/routes/assessment.py and frontend

import math
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# ─── ASSESSMENT TYPE CONSTANTS ──────────────────────────────────

ASSESSMENT_TYPES = [
    "accident",
    "insurance_claim",
    "repair_cost",
    "total_loss",
    "salvage",
    "theft_recovery",
]

# ─── ASSESSMENT PRICES ──────────────────────────────────────────

ASSESSMENT_PRICES = {
    "accident": 3500,
    "insurance_claim": 4000,
    "repair_cost": 3000,
    "total_loss": 4000,
    "salvage": 3500,
    "theft_recovery": 4000,
}

# ─── BASE REPAIR COSTS BY SEGMENT ──────────────────────────────

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

# ─── DAMAGE SEVERITY MULTIPLIERS ───────────────────────────────

SEVERITY_MULTIPLIERS = {
    "minor": 0.3,
    "moderate": 0.6,
    "major": 0.9,
    "severe": 1.2,
    "catastrophic": 1.5,
}

# ─── PARTS COST FACTORS ─────────────────────────────────────────

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
    "airbags": 0.20,
    "cooling": 0.10,
    "exhaust": 0.08,
    "fuel_system": 0.15,
    "steering": 0.18,
}

# ─── LABOUR RATE ─────────────────────────────────────────────────

LABOUR_RATE = 2500  # KES per hour

# ─── SALVAGE PERCENTAGE BY SEVERITY ────────────────────────────

SALVAGE_PERCENTAGE = {
    "minor": 0.85,
    "moderate": 0.65,
    "major": 0.45,
    "severe": 0.25,
    "catastrophic": 0.10,
}

# ─── THEFT RECOVERY CONDITION FACTORS ──────────────────────────

THEFT_RECOVERY_FACTORS = {
    "excellent": 0.95,
    "good": 0.85,
    "fair": 0.70,
    "poor": 0.50,
    "damaged": 0.30,
}

# ─── TOTAL LOSS THRESHOLD ──────────────────────────────────────

TOTAL_LOSS_THRESHOLD = 0.65  # Repair cost / market value ratio


# ─── VEHICLE SEGMENT DETECTION ──────────────────────────────────

def get_segment(make: str, model: str) -> str:
    """
    Determine vehicle segment based on make and model.
    Aligned with frontend vehicle database.
    """
    make_lower = make.lower()
    model_lower = model.lower()

    # Luxury brands
    luxury_brands = ["mercedes", "bmw", "audi", "lexus", "jaguar", "land rover", "porsche", "volvo"]
    if any(b in make_lower for b in luxury_brands):
        return "luxury"

    # SUVs
    suv_models = ["rav4", "cr-v", "x-trail", "forester", "outlander", "tucson", "sportage", "cx-5", "fortuner", "prado"]
    if any(m in model_lower for m in suv_models) or "suv" in model_lower:
        return "suv"

    # Pickups
    pickup_models = ["hilux", "ranger", "d-max", "navara", "triton"]
    if any(m in model_lower for m in pickup_models):
        return "pickup"

    # Vans
    van_models = ["hiace", "transit", "delica", "nv200", "voxy", "noah"]
    if any(m in model_lower for m in van_models):
        return "van"

    # Large sedans
    large_models = ["camry", "accord", "legacy", "mazda6", "passat", "superb", "crown"]
    if any(m in model_lower for m in large_models):
        return "large"

    # Midsize
    midsize_models = ["corolla", "civic", "axio", "premio", "allion", "elantra", "cerato", "3", "c-class"]
    if any(m in model_lower for m in midsize_models):
        return "midsize"

    # Compact
    compact_models = ["vitz", "fit", "note", "swift", "rio", "i20", "polo", "208", "yaris", "jazz"]
    if any(m in model_lower for m in compact_models):
        return "compact"

    # Small
    small_models = ["passo", "demio", "picanto", "i10", "ignis", "alto"]
    if any(m in model_lower for m in small_models):
        return "small"

    # Default
    return "compact"


# ─── REPAIR COST ESTIMATION ─────────────────────────────────────

def estimate_repair_cost(
    segment: str,
    damage_severity: str,
    parts_affected: List[str],
    labour_hours: float = 8.0,
) -> Dict[str, Any]:
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


# ─── ACCIDENT ASSESSMENT ────────────────────────────────────────

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
    inspector: Optional[Dict[str, Any]] = None,
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
    confidence = 85
    if not police_report:
        confidence -= 10
    if not description:
        confidence -= 5
    if damage_severity in ["severe", "major", "catastrophic"] and not police_report:
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
        "inspector": inspector or {},
        "generated_at": datetime.now().isoformat(),
    }
    return result


# ─── INSURANCE CLAIM ASSESSMENT ─────────────────────────────────

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
    policy_excess: float = 0,
    inspector: Optional[Dict[str, Any]] = None,
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
    estimated_payout = repair_est["total_cost"] * payout_ratio - policy_excess
    estimated_payout = max(0, math.ceil(estimated_payout / 100) * 100)

    # Check if claim exceeds vehicle value (total loss)
    loss_ratio = repair_est["total_cost"] / max(market_value, 1)
    total_loss = loss_ratio >= TOTAL_LOSS_THRESHOLD

    # Claim validity
    claim_valid = estimated_payout > 0 and not total_loss

    assessment_id = f"CLM-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

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
        "recommendation": "Total Loss" if total_loss else ("Claim Approved" if claim_valid else "Claim Denied"),
        "inspector": inspector or {},
        "generated_at": datetime.now().isoformat(),
    }
    return result


# ─── REPAIR COST ASSESSMENT ─────────────────────────────────────

def assess_repair_cost(
    make: str,
    model: str,
    year: int,
    damage_severity: str,
    parts_affected: List[str],
    market_value: Optional[int] = None,
    labour_hours: float = 8.0,
    inspector: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Standalone repair cost assessment (without incident details).
    Useful for pre-purchase or pre-repair quotes.
    """
    segment = get_segment(make, model)
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
        "inspector": inspector or {},
        "generated_at": datetime.now().isoformat(),
    }
    if market_value:
        result["market_value"] = market_value
        result["repair_ratio"] = round(repair_est["total_cost"] / max(market_value, 1), 2)
        result["total_loss"] = result["repair_ratio"] >= TOTAL_LOSS_THRESHOLD
    return result


# ─── TOTAL LOSS ASSESSMENT ──────────────────────────────────────

def assess_total_loss(
    make: str,
    model: str,
    year: int,
    market_value: int,
    repair_estimate: int,
    insurance_policy_details: str = "",
    salvage_value: Optional[int] = None,
    inspector: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Determine if a vehicle should be declared a total loss.
    """
    loss_ratio = repair_estimate / max(market_value, 1)
    total_loss = loss_ratio >= TOTAL_LOSS_THRESHOLD

    if not salvage_value:
        salvage_value = int(market_value * 0.2)

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
        "inspector": inspector or {},
        "generated_at": datetime.now().isoformat(),
    }
    return result


# ─── SALVAGE ASSESSMENT ─────────────────────────────────────────

def assess_salvage(
    make: str,
    model: str,
    year: int,
    pre_accident_value: int,
    damage_severity: str,
    parts_affected: List[str],
    inspector: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Determine salvage value of a damaged vehicle.
    """
    salvage_percent = SALVAGE_PERCENTAGE.get(damage_severity, 0.65)
    salvage_value = pre_accident_value * salvage_percent
    salvage_value = math.ceil(salvage_value / 100) * 100

    # Adjust salvage value based on parts affected
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
        "inspector": inspector or {},
        "generated_at": datetime.now().isoformat(),
    }
    return result


# ─── THEFT RECOVERY ASSESSMENT ──────────────────────────────────

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
    inspector: Optional[Dict[str, Any]] = None,
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
        "inspector": inspector or {},
        "generated_at": datetime.now().isoformat(),
    }
    return result


# ─── UNIFIED ASSESSMENT ROUTER ──────────────────────────────────

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


# ─── GET ASSESSMENT PRICE ───────────────────────────────────────

def get_assessment_price(assessment_type: str) -> int:
    """Get the price for a specific assessment type."""
    return ASSESSMENT_PRICES.get(assessment_type, 3000)


# ─── VALIDATE ASSESSMENT DATA ──────────────────────────────────

def validate_assessment_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate assessment input data.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['assessment_type']
    
    for field in required_fields:
        if not data.get(field):
            return False, f"Missing required field: {field}"
    
    assessment_type = data.get('assessment_type')
    if assessment_type not in ASSESSMENT_TYPES:
        return False, f"Invalid assessment type: {assessment_type}"
    
    # Vehicle validation
    vehicle = data.get('vehicle', {})
    if not vehicle.get('make'):
        return False, "Vehicle make is required"
    if not vehicle.get('model'):
        return False, "Vehicle model is required"
    if not vehicle.get('year'):
        return False, "Vehicle year is required"
    
    # Type-specific validation
    if assessment_type == 'accident':
        if not data.get('damage_severity'):
            return False, "Damage severity is required for accident assessment"
        if not data.get('parts_affected'):
            return False, "Parts affected is required for accident assessment"
    
    return True, None


# ─── GET ASSESSMENT FIELDS ──────────────────────────────────────

def get_assessment_fields(assessment_type: str) -> List[Dict[str, Any]]:
    """
    Get the required fields for a specific assessment type.
    Aligned with frontend assessment form.
    """
    fields_map = {
        "accident": [
            {"key": "incident_date", "label": "Incident Date", "type": "date", "required": True},
            {"key": "damage_severity", "label": "Damage Severity", "type": "select", "options": ["minor", "moderate", "major", "severe", "catastrophic"], "required": True},
            {"key": "parts_affected", "label": "Parts Affected", "type": "select", "options": ["engine", "transmission", "suspension", "brakes", "body", "paint", "electrical", "interior", "chassis", "tyres", "airbags", "cooling", "exhaust", "fuel_system", "steering"], "required": True, "multiple": True},
            {"key": "police_report", "label": "Police Report Number", "type": "text", "required": False},
            {"key": "location", "label": "Location", "type": "text", "required": False},
            {"key": "description", "label": "Description of Incident", "type": "textarea", "required": True}
        ],
        "insurance_claim": [
            {"key": "claim_number", "label": "Claim Number", "type": "text", "required": True},
            {"key": "insurance_company", "label": "Insurance Company", "type": "text", "required": True},
            {"key": "adjuster_name", "label": "Adjuster Name", "type": "text", "required": False},
            {"key": "policy_excess", "label": "Policy Excess (KES)", "type": "number", "required": False},
            {"key": "damage_severity", "label": "Damage Severity", "type": "select", "options": ["minor", "moderate", "major", "severe"], "required": True},
            {"key": "parts_affected", "label": "Parts Affected", "type": "select", "options": ["engine", "transmission", "suspension", "brakes", "body", "paint", "electrical", "interior", "chassis", "tyres"], "required": True, "multiple": True}
        ],
        "repair_cost": [
            {"key": "damage_severity", "label": "Damage Severity", "type": "select", "options": ["minor", "moderate", "major", "severe"], "required": True},
            {"key": "parts_affected", "label": "Parts Affected", "type": "select", "options": ["engine", "transmission", "suspension", "brakes", "body", "paint", "electrical", "interior", "chassis", "tyres"], "required": True, "multiple": True},
            {"key": "labour_hours", "label": "Labour Hours", "type": "number", "required": False}
        ],
        "total_loss": [
            {"key": "repair_estimate", "label": "Repair Estimate (KES)", "type": "number", "required": True},
            {"key": "policy_details", "label": "Insurance Policy Details", "type": "text", "required": False},
            {"key": "salvage_value", "label": "Estimated Salvage Value (KES)", "type": "number", "required": False}
        ],
        "salvage": [
            {"key": "damage_severity", "label": "Damage Severity", "type": "select", "options": ["minor", "moderate", "major", "severe", "catastrophic"], "required": True},
            {"key": "parts_affected", "label": "Parts Affected", "type": "select", "options": ["engine", "transmission", "suspension", "brakes", "body", "paint", "electrical", "interior", "chassis", "tyres"], "required": True, "multiple": True}
        ],
        "theft_recovery": [
            {"key": "theft_date", "label": "Theft Date", "type": "date", "required": True},
            {"key": "recovery_date", "label": "Recovery Date", "type": "date", "required": True},
            {"key": "police_station", "label": "Police Station", "type": "text", "required": True},
            {"key": "condition", "label": "Condition on Recovery", "type": "select", "options": ["excellent", "good", "fair", "poor", "damaged"], "required": True},
            {"key": "modifications", "label": "Modifications", "type": "text", "required": False}
        ]
    }
    return fields_map.get(assessment_type, [])


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    # 1. Accident Assessment
    print("=" * 60)
    print("=== Accident Assessment ===")
    print("=" * 60)
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
        description="Side impact collision at low speed.",
        inspector={"name": "John M. Valuer", "credentials": "AVM-45678"}
    )
    print(f"Assessment ID: {accident_result['assessment_id']}")
    print(f"Repair Cost: KES {accident_result['repair_estimate']['total_cost']:,}")
    print(f"Total Loss: {accident_result['total_loss']}")
    print(f"Recommendation: {accident_result['recommendation']}")

    # 2. Insurance Claim Assessment
    print("\n" + "=" * 60)
    print("=== Insurance Claim Assessment ===")
    print("=" * 60)
    claim_result = assess_insurance_claim(
        make="Honda",
        model="CR-V",
        year=2019,
        market_value=3200000,
        claim_number="CLM-2025-5678",
        insurance_company="Britam",
        damage_severity="minor",
        parts_affected=["body", "paint"],
        adjuster_name="Jane M.",
        policy_excess=50000
    )
    print(f"Assessment ID: {claim_result['assessment_id']}")
    print(f"Estimated Payout: KES {claim_result['estimated_payout']:,}")
    print(f"Claim Valid: {claim_result['claim_valid']}")

    # 3. Repair Cost Assessment
    print("\n" + "=" * 60)
    print("=== Repair Cost Assessment ===")
    print("=" * 60)
    repair_result = assess_repair_cost(
        make="Subaru",
        model="Forester",
        year=2017,
        damage_severity="moderate",
        parts_affected=["engine", "transmission", "suspension"],
        market_value=2800000,
        labour_hours=12
    )
    print(f"Assessment ID: {repair_result['assessment_id']}")
    print(f"Repair Cost: KES {repair_result['repair_estimate']['total_cost']:,}")
    print(f"Labour Hours: {repair_result['repair_estimate']['labour_hours']}")

    # 4. Total Loss Assessment
    print("\n" + "=" * 60)
    print("=== Total Loss Assessment ===")
    print("=" * 60)
    total_loss_result = assess_total_loss(
        make="Nissan",
        model="X-Trail",
        year=2016,
        market_value=2500000,
        repair_estimate=1800000,
        insurance_policy_details="Comprehensive with KES 50,000 excess"
    )
    print(f"Assessment ID: {total_loss_result['assessment_id']}")
    print(f"Total Loss: {total_loss_result['total_loss']}")
    print(f"Loss Ratio: {total_loss_result['loss_ratio']}")

    # 5. Salvage Assessment
    print("\n" + "=" * 60)
    print("=== Salvage Assessment ===")
    print("=" * 60)
    salvage_result = assess_salvage(
        make="Mercedes",
        model="C-Class",
        year=2019,
        pre_accident_value=4500000,
        damage_severity="major",
        parts_affected=["engine", "body", "chassis"]
    )
    print(f"Assessment ID: {salvage_result['assessment_id']}")
    print(f"Salvage Value: KES {salvage_result['salvage_value']:,}")
    print(f"Salvage Percentage: {salvage_result['salvage_percentage'] * 100}%")

    # 6. Theft Recovery Assessment
    print("\n" + "=" * 60)
    print("=== Theft Recovery Assessment ===")
    print("=" * 60)
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
    print(f"Assessment ID: {theft_result['assessment_id']}")
    print(f"Recovered Value: KES {theft_result['vehicle']['recovered_value']:,}")
    print(f"Value Loss: KES {theft_result['value_loss']:,}")
    print(f"Loss Percentage: {theft_result['loss_percentage']}%")

    # 7. Unified Entry Point
    print("\n" + "=" * 60)
    print("=== Unified Assessment Entry Point ===")
    print("=" * 60)
    unified_result = assess(
        "accident",
        make="Toyota",
        model="Corolla",
        year=2020,
        market_value=2800000,
        damage_severity="minor",
        parts_affected=["body", "paint"],
        incident_date="2025-02-01",
        location="Mombasa"
    )
    print(f"Assessment ID: {unified_result['assessment_id']}")
    print(f"Repair Cost: KES {unified_result['repair_estimate']['total_cost']:,}")
