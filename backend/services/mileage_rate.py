# mileage_rate.py – AUTO-V Mileage Rate Engine (Production-Ready)

import math
import random
from datetime import datetime
from typing import Dict, Any, Optional, List

# Default values (will be overridden by system_settings)
DEFAULT_FUEL_PRICE = 190.0
DEFAULT_KM_PER_LITER = 12.0
DEFAULT_MAINTENANCE_BASE = 8.0
DEFAULT_DEPRECIATION_BASE = 6.0
DEFAULT_INSURANCE_BASE = 3.0
DEFAULT_OVERHEAD_BASE = 4.0

# Vehicle type multipliers
VEHICLE_MULTIPLIER = {
    "saloon": 1.00,
    "suv": 1.25,
    "pickup": 1.30,
    "truck": 1.60,
    "van": 1.40,
    "luxury": 1.80,
    "motorcycle": 0.60,
    "hatchback": 0.95,
    "sedan": 1.00,
    "crossover": 1.10,
    "minibus": 1.45,
    "bus": 1.80,
}

# Usage multipliers
USAGE_MULTIPLIER = {
    "personal": 1.00,
    "commercial": 1.20,
    "fleet": 1.10,
    "uber": 1.25,
    "delivery": 1.30,
    "logistics": 1.35,
    "government": 1.15,
    "ngo": 1.05,
}

# Region multipliers (Kenya)
REGION_MULTIPLIER = {
    "nairobi": 1.10,
    "mombasa": 1.05,
    "kisumu": 1.00,
    "nakuru": 1.00,
    "eldoret": 0.98,
    "thika": 0.97,
    "malindi": 1.02,
    "other": 1.00,
}

# Road condition multipliers
ROAD_CONDITION = {
    "excellent": 0.95,
    "good": 1.00,
    "fair": 1.10,
    "poor": 1.25,
}

# Purpose factors (adjust final rate based on purpose)
PURPOSE_FACTORS = {
    "mileage_rate_report": 1.00,
    "vehicle_running_cost_analysis": 1.05,
    "fleet_running_cost_analysis": 0.95,
    "travel_reimbursement_report": 1.00,
}

# Purpose -> key mapping for system_settings
PURPOSE_FEE_KEYS = {
    "mileage_rate_report": "mileage_fee",
    "vehicle_running_cost_analysis": "mileage_fee",
    "fleet_running_cost_analysis": "mileage_fee",
    "travel_reimbursement_report": "mileage_fee",
}


def get_system_settings() -> Dict[str, float]:
    """
    Fetch system settings for mileage calculation.
    In production, this would query the database.
    For now, returns defaults.
    """
    # In production, this would be:
    # SELECT setting_key, setting_value FROM system_settings
    # WHERE setting_key IN ('fuel_price', 'km_per_liter', 'maintenance_base', ...)
    # and return a dict.

    # Placeholder – real implementation uses Supabase
    return {
        "fuel_price": DEFAULT_FUEL_PRICE,
        "km_per_liter": DEFAULT_KM_PER_LITER,
        "maintenance_base": DEFAULT_MAINTENANCE_BASE,
        "depreciation_base": DEFAULT_DEPRECIATION_BASE,
        "insurance_base": DEFAULT_INSURANCE_BASE,
        "overhead_base": DEFAULT_OVERHEAD_BASE,
    }


def calculate_mileage_rate(
    vehicle_type: str,
    usage: str,
    region: str,
    road_condition: str,
    purpose: str = "mileage_rate_report",
    fuel_price: Optional[float] = None,
    km_per_liter: Optional[float] = None,
    maintenance_base: Optional[float] = None,
    depreciation_base: Optional[float] = None,
    insurance_base: Optional[float] = None,
    overhead_base: Optional[float] = None,
    monthly_km: int = 2000,
    yearly_km: int = 24000,
) -> Dict[str, Any]:
    """
    Calculate a comprehensive mileage rate report.

    Args:
        vehicle_type: saloon, suv, pickup, truck, van, luxury, motorcycle
        usage: personal, commercial, fleet, uber, delivery
        region: nairobi, mombasa, kisumu, nakuru, eldoret, other
        road_condition: excellent, good, fair, poor
        purpose: mileage_rate_report, vehicle_running_cost_analysis, fleet_running_cost_analysis, travel_reimbursement_report
        fuel_price: override default
        km_per_liter: override default
        maintenance_base: override default
        depreciation_base: override default
        insurance_base: override default
        overhead_base: override default
        monthly_km: distance driven per month (for projection)
        yearly_km: distance driven per year (for projection)

    Returns:
        Dictionary with cost_per_km, projections, breakdown, and purpose-specific adjustments.
    """
    # Get system settings (or use overrides)
    settings = get_system_settings()

    fuel_price = fuel_price or settings.get("fuel_price", DEFAULT_FUEL_PRICE)
    km_per_liter = km_per_liter or settings.get("km_per_liter", DEFAULT_KM_PER_LITER)
    maintenance_base = maintenance_base or settings.get("maintenance_base", DEFAULT_MAINTENANCE_BASE)
    depreciation_base = depreciation_base or settings.get("depreciation_base", DEFAULT_DEPRECIATION_BASE)
    insurance_base = insurance_base or settings.get("insurance_base", DEFAULT_INSURANCE_BASE)
    overhead_base = overhead_base or settings.get("overhead_base", DEFAULT_OVERHEAD_BASE)

    # ---- Fuel cost per km ----
    fuel_cost_per_km = fuel_price / km_per_liter

    # ---- Base cost per km ----
    base_cost_per_km = (
        fuel_cost_per_km
        + maintenance_base
        + depreciation_base
        + insurance_base
        + overhead_base
    )

    # ---- Apply multipliers ----
    vehicle_factor = VEHICLE_MULTIPLIER.get(vehicle_type.lower(), 1.0)
    usage_factor = USAGE_MULTIPLIER.get(usage.lower(), 1.0)
    region_factor = REGION_MULTIPLIER.get(region.lower(), 1.0)
    road_factor = ROAD_CONDITION.get(road_condition.lower(), 1.0)
    purpose_factor = PURPOSE_FACTORS.get(purpose, 1.0)

    # ---- Final cost per KM ----
    cost_per_km = (
        base_cost_per_km
        * vehicle_factor
        * usage_factor
        * region_factor
        * road_factor
        * purpose_factor
    )
    cost_per_km = round(cost_per_km, 2)

    # ---- Projections ----
    monthly_cost = round(cost_per_km * monthly_km)
    yearly_cost = round(cost_per_km * yearly_km)

    # ---- Generate mileage rate report ID ----
    report_id = f"MR-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    # ---- Build result ----
    result = {
        "report_id": report_id,
        "cost_per_km": cost_per_km,
        "cost_per_month": monthly_cost,
        "cost_per_year": yearly_cost,
        "monthly_km": monthly_km,
        "yearly_km": yearly_km,
        "fuel_cost_per_km": round(fuel_cost_per_km, 2),
        "breakdown": {
            "base_cost_per_km": round(base_cost_per_km, 2),
            "vehicle_factor": vehicle_factor,
            "usage_factor": usage_factor,
            "region_factor": region_factor,
            "road_factor": road_factor,
            "purpose_factor": purpose_factor,
        },
        "components": {
            "fuel": round(fuel_cost_per_km, 2),
            "maintenance": maintenance_base,
            "depreciation": depreciation_base,
            "insurance": insurance_base,
            "overhead": overhead_base,
        },
        "inputs": {
            "vehicle_type": vehicle_type,
            "usage": usage,
            "region": region,
            "road_condition": road_condition,
            "purpose": purpose,
            "fuel_price": fuel_price,
            "km_per_liter": km_per_liter,
        },
        "purpose": purpose,
        "generated_at": datetime.now().isoformat(),
    }

    return result


def quick_mileage_estimate(vehicle_type: str) -> float:
    """
    Simple estimate for instant UI display (used in Quick Value Check).
    Returns cost per km as float.
    """
    base = 35.0  # KES per km baseline (Kenya average)
    factor = VEHICLE_MULTIPLIER.get(vehicle_type.lower(), 1.0)
    return round(base * factor, 2)


def get_mileage_purpose_fee(purpose: str) -> float:
    """
    Get the fee for a specific mileage purpose from system_settings.
    """
    # In production, this would query the database.
    # For now, return default fee.
    return 1500.0  # Default KES


# -------------------- Integration with assessment.py style --------------------
def run_mileage_rate(
    vehicle_type: str,
    usage: str,
    region: str,
    road_condition: str,
    purpose: str = "mileage_rate_report",
    monthly_km: int = 2000,
    yearly_km: int = 24000,
) -> Dict[str, Any]:
    """
    Unified entry point for mileage rate calculation.
    Matches the style of valuation.py, inspection.py, assessment.py.
    """
    result = calculate_mileage_rate(
        vehicle_type=vehicle_type,
        usage=usage,
        region=region,
        road_condition=road_condition,
        purpose=purpose,
        monthly_km=monthly_km,
        yearly_km=yearly_km,
    )
    return result


# -------------------- Example usage --------------------
if __name__ == "__main__":
    # Full mileage rate report
    result = calculate_mileage_rate(
        vehicle_type="suv",
        usage="uber",
        region="nairobi",
        road_condition="fair",
        purpose="mileage_rate_report",
        monthly_km=2500,
        yearly_km=30000,
    )

    print("MILEAGE RATE REPORT")
    print("-------------------")
    print(f"Report ID: {result['report_id']}")
    print(f"Cost per KM: KES {result['cost_per_km']}")
    print(f"Monthly (2500km): KES {result['cost_per_month']:,}")
    print(f"Yearly (30000km): KES {result['cost_per_year']:,}")
    print(f"Fuel Cost/KM: KES {result['fuel_cost_per_km']}")
    print("\nBreakdown:")
    for key, val in result["breakdown"].items():
        print(f"  {key}: {val}")
    print("\nComponents (KES per km):")
    for key, val in result["components"].items():
        print(f"  {key}: {val}")

    # Quick estimate
    print("\nQuick Estimate:")
    print(f"SUV: KES {quick_mileage_estimate('suv')}/km")
