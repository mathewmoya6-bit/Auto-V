# valuation.py – AUTO-V AI Valuation Engine

import math
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

# Base prices for common makes in Kenya (as of 2026)
BASE_PRICES: Dict[str, Dict[str, int]] = {
    "toyota": {
        "default": 1800000,
        "axio": 2200000,
        "corolla": 2500000,
        "camry": 3800000,
        "rav4": 3500000,
        "land cruiser": 12000000,
        "prado": 8000000,
        "hilux": 4500000,
        "fortuner": 5500000,
        "premio": 2600000,
        "allion": 2700000,
        "vitz": 1400000,
        "passo": 1500000,
        "sienta": 1800000,
        "noah": 2800000,
        "voxy": 2900000,
        "hiace": 3500000,
        "other": 1800000,
    },
    "honda": {
        "default": 1700000,
        "fit": 1600000,
        "civic": 2800000,
        "accord": 3500000,
        "cr-v": 3200000,
        "hr-v": 2700000,
        "odyssey": 3800000,
        "pilot": 4000000,
        "other": 1700000,
    },
    "nissan": {
        "default": 1500000,
        "note": 1400000,
        "sunny": 1500000,
        "x-trail": 2800000,
        "patrol": 8500000,
        "qashqai": 2600000,
        "juke": 2000000,
        "leaf": 3000000,
        "other": 1500000,
    },
    "subaru": {
        "default": 2200000,
        "impreza": 2400000,
        "forester": 3200000,
        "outback": 3800000,
        "legacy": 3000000,
        "xv": 2800000,
        "wrx": 3500000,
        "other": 2200000,
    },
    "mazda": {
        "default": 1600000,
        "3": 2000000,
        "6": 2800000,
        "cx-3": 2500000,
        "cx-5": 3200000,
        "mx-5": 4000000,
        "demio": 1600000,
        "other": 1600000,
    },
    "mercedes-benz": {
        "default": 3500000,
        "c-class": 4500000,
        "e-class": 6500000,
        "s-class": 12000000,
        "gle": 8000000,
        "glc": 6000000,
        "gla": 5000000,
        "a-class": 4000000,
        "b-class": 4200000,
        "other": 3500000,
    },
    "bmw": {
        "default": 3500000,
        "3 series": 4200000,
        "5 series": 6000000,
        "x3": 5200000,
        "x5": 7000000,
        "1 series": 3600000,
        "7 series": 9000000,
        "x1": 4000000,
        "x7": 10000000,
        "other": 3500000,
    },
    "audi": {
        "default": 3000000,
        "a3": 3200000,
        "a4": 3800000,
        "a6": 5000000,
        "q3": 3500000,
        "q5": 4500000,
        "q7": 6500000,
        "tt": 4200000,
        "e-tron": 6000000,
        "other": 3000000,
    },
    "volkswagen": {
        "default": 1800000,
        "golf": 2400000,
        "polo": 1800000,
        "passat": 3200000,
        "tiguan": 3500000,
        "touareg": 5000000,
        "jetta": 2600000,
        "beetle": 2800000,
        "other": 1800000,
    },
    "ford": {
        "default": 1700000,
        "focus": 2000000,
        "fiesta": 1500000,
        "mustang": 6000000,
        "ranger": 4000000,
        "explorer": 4500000,
        "escape": 3200000,
        "transit": 3500000,
        "other": 1700000,
    },
    "isuzu": {
        "default": 3000000,
        "d-max": 3800000,
        "mu-x": 4500000,
        "n-series": 3500000,
        "f-series": 5000000,
        "other": 3000000,
    },
    "mitsubishi": {
        "default": 1600000,
        "outlander": 2800000,
        "pajero": 5000000,
        "lancer": 2000000,
        "asx": 2300000,
        "delica": 3200000,
        "minica": 1200000,
        "other": 1600000,
    },
    "peugeot": {
        "default": 1500000,
        "208": 1800000,
        "308": 2200000,
        "508": 3000000,
        "2008": 2200000,
        "3008": 2800000,
        "5008": 3200000,
        "other": 1500000,
    },
    "land rover": {
        "default": 4500000,
        "defender": 7000000,
        "discovery": 6000000,
        "range rover": 12000000,
        "evoque": 5000000,
        "velar": 6500000,
        "sport": 8000000,
        "other": 4500000,
    },
    "jaguar": {
        "default": 4000000,
        "xe": 4500000,
        "xf": 5500000,
        "xj": 7000000,
        "f-pace": 6000000,
        "e-pace": 5000000,
        "i-pace": 7000000,
        "other": 4000000,
    },
    "lexus": {
        "default": 4000000,
        "is": 4500000,
        "es": 5000000,
        "ls": 8000000,
        "rx": 6000000,
        "nx": 5000000,
        "ux": 4500000,
        "lx": 10000000,
        "gx": 7000000,
        "other": 4000000,
    },
    "volvo": {
        "default": 3000000,
        "s60": 3500000,
        "s90": 4500000,
        "v60": 3800000,
        "xc40": 4000000,
        "xc60": 5000000,
        "xc90": 6500000,
        "other": 3000000,
    },
    "hyundai": {
        "default": 1500000,
        "i10": 1200000,
        "i20": 1500000,
        "i30": 2000000,
        "tucson": 2800000,
        "santa fe": 3500000,
        "palisade": 4000000,
        "kona": 2500000,
        "other": 1500000,
    },
    "kia": {
        "default": 1400000,
        "picanto": 1200000,
        "rio": 1500000,
        "cerato": 2000000,
        "sportage": 2800000,
        "sorento": 3500000,
        "stinger": 4000000,
        "telluride": 4500000,
        "other": 1400000,
    },
    "suzuki": {
        "default": 1300000,
        "swift": 1500000,
        "jimny": 2200000,
        "vitara": 2500000,
        "baleno": 1700000,
        "s-cross": 2300000,
        "ignis": 1400000,
        "other": 1300000,
    },
    "other": {
        "default": 1200000,
        "other": 1200000,
    }
}

# Condition multipliers
CONDITION_MAP = {
    "excellent": 1.00,
    "good": 0.92,
    "fair": 0.85,
    "poor": 0.70,
}

# Accident adjustments
ACCIDENT_FACTORS = {
    "none": 1.00,
    "minor": 0.85,
    "moderate": 0.65,
    "major": 0.40,
}

# Service history adjustments
SERVICE_FACTORS = {
    "full": 1.00,
    "partial": 0.90,
    "none": 0.75,
}

# Owner count adjustments
OWNER_FACTORS = {
    1: 1.00,
    2: 0.92,
    3: 0.85,
    4: 0.75,
}

# Usage adjustments
USAGE_FACTORS = {
    "personal": 1.00,
    "commercial": 0.80,
    "fleet": 0.75,
    "rental": 0.70,
}

# Import status adjustments
IMPORT_FACTORS = {
    "local": 1.00,
    "imported": 0.85,
    "new import": 0.95,
}

# Warranty adjustments
WARRANTY_FACTORS = {
    "active": 1.05,
    "expired": 1.00,
    "none": 0.95,
}

# Modification adjustments
MOD_FACTORS = {
    "none": 1.00,
    "minor": 1.02,
    "major": 0.90,
    "extensive": 0.80,
}

# Regional price adjustments (relative to Nairobi as base)
REGION_FACTORS = {
    "nairobi": 1.05,
    "mombasa": 1.02,
    "kisumu": 1.00,
    "nakuru": 0.98,
    "eldoret": 0.97,
    "national": 1.00,
}

# Purpose-specific adjustments (applied to final market value)
PURPOSE_FACTORS = {
    "market_value": 1.00,
    "insurance": 1.10,
    "bank_financing": 0.95,
    "sale": 0.90,
    "purchase": 0.95,
    "fleet": 0.85,
    "tax": 0.80,
    "internal_audit": 0.90,
}


def get_base_price(make: str, model: str) -> int:
    """
    Get the base price for a given make and model.
    Falls back to default if model not found.
    """
    make_lower = make.lower().strip()
    model_lower = model.lower().strip()

    make_data = BASE_PRICES.get(make_lower, BASE_PRICES["other"])
    # Try exact model match, else fallback to "default"
    price = make_data.get(model_lower)
    if price is None:
        price = make_data.get("default", 1200000)
    return price


def calculate_value(
    make: str,
    model: str,
    year: int,
    odometer: int,
    condition: str,
    accident_history: str = "none",
    service_history: str = "full",
    owners: int = 1,
    usage: str = "personal",
    import_status: str = "local",
    warranty: str = "expired",
    modifications: str = "none",
    region: str = "nairobi",
    purpose: str = "market_value",
    valuation_methodology: str = "market_comparison",
    current_year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calculate a professional vehicle valuation with full audit trail.

    Args:
        make: Vehicle make (e.g., Toyota, BMW)
        model: Vehicle model (e.g., Axio, 3 Series)
        year: Year of manufacture
        odometer: Mileage in kilometers
        condition: Excellent, Good, Fair, Poor
        accident_history: None, Minor, Moderate, Major
        service_history: Full, Partial, None
        owners: Number of previous owners (1-4+)
        usage: Personal, Commercial, Fleet, Rental
        import_status: Local, Imported, New Import
        warranty: Active, Expired, None
        modifications: None, Minor, Major, Extensive
        region: Nairobi, Mombasa, Kisumu, Nakuru, Eldoret, National
        purpose: Market Value, Insurance, Bank Financing, Sale, Purchase, Fleet, Tax, Internal Audit
        valuation_methodology: Market Comparison, Cost Approach, Income Approach, Hybrid
        current_year: Override current year (defaults to system year)

    Returns:
        Dictionary with valuation details, including:
        - market_value
        - insurance_value
        - forced_sale_value
        - confidence_score
        - risk_score
        - condition_score
        - valuation_id
        - inspector details (if provided)
        - comparables
        - factors used
    """
    # Default current year if not provided
    if current_year is None:
        current_year = datetime.now().year

    # ---- 1. Base Price ----
    base_price = get_base_price(make, model)

    # ---- 2. Age & Depreciation ----
    age = current_year - year
    # Depreciation curve: higher for newer cars, tapers off
    if age <= 1:
        dep_rate = 0.05
    elif age <= 3:
        dep_rate = 0.08
    elif age <= 5:
        dep_rate = 0.10
    elif age <= 8:
        dep_rate = 0.12
    elif age <= 12:
        dep_rate = 0.15
    else:
        dep_rate = 0.18
    dep_factor = (1 - dep_rate) ** age

    # ---- 3. Mileage Adjustment ----
    # Expected mileage: 15,000 km/year for personal use
    expected_mileage = max(age * 15000, 1)
    mileage_ratio = odometer / expected_mileage

    if mileage_ratio <= 0.8:
        mileage_factor = 1.05
    elif mileage_ratio <= 1.0:
        mileage_factor = 1.00
    elif mileage_ratio <= 1.2:
        mileage_factor = 0.92
    elif mileage_ratio <= 1.5:
        mileage_factor = 0.82
    elif mileage_ratio <= 2.0:
        mileage_factor = 0.70
    else:
        mileage_factor = 0.55

    # ---- 4. Condition Factor ----
    cond_lower = condition.lower().strip()
    condition_factor = CONDITION_MAP.get(cond_lower, 0.85)

    # ---- 5. Accident Factor ----
    accident_lower = accident_history.lower().strip()
    accident_factor = ACCIDENT_FACTORS.get(accident_lower, 1.00)

    # ---- 6. Service History Factor ----
    service_lower = service_history.lower().strip()
    service_factor = SERVICE_FACTORS.get(service_lower, 1.00)

    # ---- 7. Owner Factor ----
    owner_key = min(owners, 4)
    owner_factor = OWNER_FACTORS.get(owner_key, 0.75)

    # ---- 8. Usage Factor ----
    usage_lower = usage.lower().strip()
    usage_factor = USAGE_FACTORS.get(usage_lower, 1.00)

    # ---- 9. Import Factor ----
    import_lower = import_status.lower().strip()
    import_factor = IMPORT_FACTORS.get(import_lower, 1.00)

    # ---- 10. Warranty Factor ----
    warranty_lower = warranty.lower().strip()
    warranty_factor = WARRANTY_FACTORS.get(warranty_lower, 1.00)

    # ---- 11. Modification Factor ----
    mod_lower = modifications.lower().strip()
    mod_factor = MOD_FACTORS.get(mod_lower, 1.00)

    # ---- 12. Region Factor ----
    region_lower = region.lower().strip()
    region_factor = REGION_FACTORS.get(region_lower, 1.00)

    # ---- 13. Purpose Factor ----
    purpose_lower = purpose.lower().strip().replace(" ", "_")
    purpose_factor = PURPOSE_FACTORS.get(purpose_lower, 1.00)

    # ---- 14. Calculate Market Value ----
    market_value = (
        base_price
        * dep_factor
        * mileage_factor
        * condition_factor
        * accident_factor
        * service_factor
        * owner_factor
        * usage_factor
        * import_factor
        * warranty_factor
        * mod_factor
        * region_factor
        * purpose_factor
    )
    # Floor value
    market_value = max(market_value, 100000)
    # Round to nearest 1000
    market_value = round(market_value / 1000) * 1000

    # ---- 15. Derived Values ----
    insurance_value = round(market_value * 1.12 / 1000) * 1000
    forced_sale_value = round(market_value * 0.72 / 1000) * 1000

    # ---- 16. Confidence Score ----
    confidence = 100
    if not make or make.lower() == "other":
        confidence -= 10
    if not model or model.lower() == "other":
        confidence -= 5
    if age > 15:
        confidence -= 10
    if odometer < 100:
        confidence -= 5
    # Condition scoring: average of inspection scores would be used in real app
    # Here we use condition factor as proxy
    if condition_factor < 0.8:
        confidence -= 10
    if accident_lower == "major":
        confidence -= 15
    elif accident_lower == "moderate":
        confidence -= 10
    if service_lower == "none":
        confidence -= 10
    if owners > 2:
        confidence -= 5
    if mod_lower == "extensive":
        confidence -= 10
    confidence = max(0, min(100, confidence))

    # ---- 17. Risk Score (inverse of confidence) ----
    risk_score = 100 - confidence

    # ---- 18. Condition Score (0-10) ----
    # Map condition factor to a 0-10 scale
    condition_score = round(condition_factor * 10, 1)

    # ---- 19. Generate Comparable Vehicles ----
    comparables = _generate_comparables(make, model, year, market_value)

    # ---- 20. Valuation ID ----
    valuation_id = f"VAL-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    # ---- 21. Build result object ----
    result = {
        "valuation_id": valuation_id,
        "market_value": market_value,
        "insurance_value": insurance_value,
        "forced_sale_value": forced_sale_value,
        "confidence_score": confidence,
        "risk_score": risk_score,
        "condition_score": condition_score,
        "valuation_methodology": valuation_methodology,
        "purpose": purpose,
        "region": region,
        "vehicle": {
            "make": make,
            "model": model,
            "year": year,
            "odometer": odometer,
            "condition": condition,
            "accident_history": accident_history,
            "service_history": service_history,
            "owners": owners,
            "usage": usage,
            "import_status": import_status,
            "warranty": warranty,
            "modifications": modifications,
        },
        "factors": {
            "base_price": base_price,
            "depreciation_factor": round(dep_factor, 3),
            "mileage_factor": round(mileage_factor, 3),
            "condition_factor": round(condition_factor, 3),
            "accident_factor": round(accident_factor, 3),
            "service_factor": round(service_factor, 3),
            "owner_factor": round(owner_factor, 3),
            "usage_factor": round(usage_factor, 3),
            "import_factor": round(import_factor, 3),
            "warranty_factor": round(warranty_factor, 3),
            "modification_factor": round(mod_factor, 3),
            "region_factor": round(region_factor, 3),
            "purpose_factor": round(purpose_factor, 3),
        },
        "comparables": comparables,
        "generated_at": datetime.now().isoformat(),
        "report_date": datetime.now().strftime("%Y-%m-%d"),
    }

    return result


def _generate_comparables(make: str, model: str, year: int, market_value: int) -> List[Dict[str, Any]]:
    """
    Generate a list of comparable vehicles for the report.
    """
    comparables = []
    # Generate 3 comps with slight variations
    for i in range(1, 4):
        comp_year = year + (i - 2)  # -1, 0, +1 year
        comp_price = market_value * (0.95 + 0.05 * i)  # 95%, 100%, 105%
        comp_odometer = max(10000, 50000 + (i - 2) * 20000)  # variations in mileage

        comparables.append({
            "make": make,
            "model": model,
            "year": comp_year,
            "odometer": comp_odometer,
            "condition": "Good" if i != 2 else "Excellent",
            "price": round(comp_price / 1000) * 1000,
        })
    return comparables


# -------------------- Helper for quick valuations --------------------
def quick_estimate(
    make: str,
    model: str,
    year: int,
    odometer: int,
    condition: str = "good",
) -> int:
    """
    Fast market value estimate without full audit trail (used for Instant Check).
    Returns estimated market value as integer.
    """
    result = calculate_value(
        make=make,
        model=model,
        year=year,
        odometer=odometer,
        condition=condition,
        accident_history="none",
        service_history="full",
        owners=1,
        usage="personal",
        import_status="local",
        warranty="expired",
        modifications="none",
        region="nairobi",
        purpose="market_value",
    )
    return result["market_value"]


# -------------------- Example usage --------------------
if __name__ == "__main__":
    # Test valuation
    vehicle = {
        "make": "toyota",
        "model": "axio",
        "year": 2018,
        "odometer": 85000,
        "condition": "good",
        "accident_history": "none",
        "service_history": "full",
        "owners": 1,
        "usage": "personal",
        "import_status": "local",
        "warranty": "expired",
        "modifications": "none",
        "region": "nairobi",
        "purpose": "insurance",
    }

    result = calculate_value(**vehicle)
    print("Valuation Result:")
    print(f"  Market Value: KES {result['market_value']:,}")
    print(f"  Insurance Value: KES {result['insurance_value']:,}")
    print(f"  Forced Sale Value: KES {result['forced_sale_value']:,}")
    print(f"  Confidence: {result['confidence_score']}%")
    print(f"  Condition Score: {result['condition_score']}/10")
    print("  Factors:")
    for key, val in result["factors"].items():
        print(f"    {key}: {val}")
    print("  Comparables:")
    for comp in result["comparables"]:
        print(f"    {comp['make']} {comp['model']} ({comp['year']}) - KES {comp['price']:,}")
