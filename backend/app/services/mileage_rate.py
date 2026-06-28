# services/mileage_rate.py – AUTO-V Mileage Rate Engine (Production-Ready)
# Aligned with api/routes/mileage.py and frontend mileage calculator

import math
import random
from datetime import datetime
from typing import Dict, Any, Optional, List

# ─── DEFAULT VALUES ──────────────────────────────────────────────
# Will be overridden by system_settings or frontend inputs

DEFAULT_FUEL_PRICES = {
    'petrol': 199.15,
    'diesel': 185.00,
    'hybrid': 199.15,
    'lpg': 120.00,
    'electric': 20.00
}

DEFAULT_FUEL_PRICE = 199.15
DEFAULT_KM_PER_LITER = 15.0
DEFAULT_MAINTENANCE_BASE = 8.0
DEFAULT_DEPRECIATION_BASE = 6.0
DEFAULT_INSURANCE_BASE = 3.0
DEFAULT_OVERHEAD_BASE = 4.0
DEFAULT_RISK_RESERVE = 0.05

# ─── VEHICLE TYPE MULTIPLIERS ────────────────────────────────────

VEHICLE_MULTIPLIER = {
    "saloon": 1.00,
    "sedan": 1.00,
    "hatchback": 0.95,
    "suv": 1.25,
    "crossover": 1.10,
    "pickup": 1.30,
    "truck": 1.60,
    "van": 1.40,
    "minibus": 1.45,
    "bus": 1.80,
    "luxury": 1.80,
    "motorcycle": 0.60,
}

# ─── VEHICLE DATABASE ────────────────────────────────────────────
# Matches frontend vehicleDatabase and api/routes/mileage.py

VEHICLE_DATABASE = {
    'Toyota Axio': {'basePrice': 2500000, 'residual': 800000, 'economy': 16, 'insurance': 65000, 'service': 35000, 'repairs': 25000, 'tyres': 40000, 'licence': 15000, 'finance': 50000},
    'Toyota Corolla': {'basePrice': 2800000, 'residual': 900000, 'economy': 15, 'insurance': 70000, 'service': 38000, 'repairs': 28000, 'tyres': 42000, 'licence': 15000, 'finance': 55000},
    'Toyota Camry': {'basePrice': 4500000, 'residual': 1500000, 'economy': 12, 'insurance': 100000, 'service': 50000, 'repairs': 40000, 'tyres': 60000, 'licence': 20000, 'finance': 80000},
    'Toyota RAV4': {'basePrice': 4200000, 'residual': 1400000, 'economy': 13, 'insurance': 95000, 'service': 48000, 'repairs': 38000, 'tyres': 55000, 'licence': 20000, 'finance': 75000},
    'Toyota Land Cruiser': {'basePrice': 12000000, 'residual': 4000000, 'economy': 8, 'insurance': 200000, 'service': 100000, 'repairs': 80000, 'tyres': 100000, 'licence': 40000, 'finance': 200000},
    'Toyota Prado': {'basePrice': 8000000, 'residual': 2800000, 'economy': 10, 'insurance': 150000, 'service': 80000, 'repairs': 60000, 'tyres': 80000, 'licence': 30000, 'finance': 150000},
    'Toyota Hilux': {'basePrice': 4500000, 'residual': 1500000, 'economy': 12, 'insurance': 100000, 'service': 50000, 'repairs': 40000, 'tyres': 60000, 'licence': 25000, 'finance': 100000},
    'Toyota Fortuner': {'basePrice': 5500000, 'residual': 1800000, 'economy': 11, 'insurance': 120000, 'service': 60000, 'repairs': 45000, 'tyres': 70000, 'licence': 25000, 'finance': 120000},
    'Honda Civic': {'basePrice': 3200000, 'residual': 1100000, 'economy': 15, 'insurance': 80000, 'service': 40000, 'repairs': 30000, 'tyres': 45000, 'licence': 15000, 'finance': 70000},
    'Honda Accord': {'basePrice': 4000000, 'residual': 1300000, 'economy': 13, 'insurance': 90000, 'service': 45000, 'repairs': 35000, 'tyres': 50000, 'licence': 18000, 'finance': 80000},
    'Nissan X-Trail': {'basePrice': 3500000, 'residual': 1200000, 'economy': 14, 'insurance': 85000, 'service': 42000, 'repairs': 32000, 'tyres': 48000, 'licence': 18000, 'finance': 70000},
    'Subaru Forester': {'basePrice': 3800000, 'residual': 1300000, 'economy': 13, 'insurance': 90000, 'service': 50000, 'repairs': 35000, 'tyres': 50000, 'licence': 20000, 'finance': 80000},
    'Mercedes C-Class': {'basePrice': 5000000, 'residual': 1800000, 'economy': 12, 'insurance': 120000, 'service': 60000, 'repairs': 45000, 'tyres': 65000, 'licence': 25000, 'finance': 120000},
    'BMW 3 Series': {'basePrice': 4800000, 'residual': 1700000, 'economy': 12, 'insurance': 115000, 'service': 58000, 'repairs': 42000, 'tyres': 62000, 'licence': 25000, 'finance': 115000}
}

# ─── USAGE MULTIPLIERS ──────────────────────────────────────────

USAGE_MULTIPLIER = {
    "personal": 1.00,
    "business": 1.00,
    "commercial": 1.20,
    "fleet": 1.10,
    "uber": 1.25,
    "delivery": 1.30,
    "logistics": 1.35,
    "government": 1.15,
    "ngo": 1.05,
    "private": 1.00,
}

# ─── REGION MULTIPLIERS (Kenya) ─────────────────────────────────

REGION_MULTIPLIER = {
    "nairobi": 1.10,
    "mombasa": 1.05,
    "kisumu": 1.00,
    "nakuru": 1.00,
    "eldoret": 0.98,
    "thika": 0.97,
    "malindi": 1.02,
    "rural": 0.92,
    "other": 1.00,
}

# ─── ROAD CONDITION MULTIPLIERS ─────────────────────────────────

ROAD_CONDITION = {
    "excellent": 0.95,
    "good": 1.00,
    "fair": 1.10,
    "poor": 1.25,
    "highway": 0.85,
    "mixed": 1.00,
    "urban": 1.10,
    "rural": 0.95,
    "offroad": 1.25,
}

# ─── DRIVER BEHAVIOUR MULTIPLIERS ──────────────────────────────

DRIVER_BEHAVIOUR = {
    "conservative": 0.90,
    "normal": 1.00,
    "aggressive": 1.12,
}

# ─── MAINTENANCE QUALITY MULTIPLIERS ────────────────────────────

MAINTENANCE_QUALITY = {
    "dealer": 1.15,
    "independent": 1.00,
    "poor": 1.30,
}

# ─── JOURNEY PURPOSE FACTORS ────────────────────────────────────

JOURNEY_PURPOSE = {
    "business": 1.00,
    "ngo": 0.95,
    "government": 0.90,
    "private": 1.00,
    "fleet": 0.92,
}

# ─── PURPOSE FACTORS (Final rate adjustment) ────────────────────

PURPOSE_FACTORS = {
    "mileage_rate_report": 1.00,
    "vehicle_running_cost_analysis": 1.05,
    "fleet_running_cost_analysis": 0.95,
    "travel_reimbursement_report": 1.00,
    "valuation": 1.00,
    "inspection": 1.00,
    "assessment": 1.00,
}

# ─── PURPOSE FEE KEYS ───────────────────────────────────────────

PURPOSE_FEE_KEYS = {
    "mileage_rate_report": "mileage_fee",
    "vehicle_running_cost_analysis": "mileage_fee",
    "fleet_running_cost_analysis": "mileage_fee",
    "travel_reimbursement_report": "mileage_fee",
}


# ─── SYSTEM SETTINGS ─────────────────────────────────────────────

def get_system_settings() -> Dict[str, float]:
    """
    Fetch system settings for mileage calculation.
    In production, this would query the database.
    For now, returns defaults.
    """
    # In production, this would be:
    # SELECT setting_key, setting_value FROM system_settings
    # WHERE setting_key IN ('fuel_price', 'km_per_liter', 'maintenance_base', ...)
    
    return {
        "fuel_price": DEFAULT_FUEL_PRICE,
        "km_per_liter": DEFAULT_KM_PER_LITER,
        "maintenance_base": DEFAULT_MAINTENANCE_BASE,
        "depreciation_base": DEFAULT_DEPRECIATION_BASE,
        "insurance_base": DEFAULT_INSURANCE_BASE,
        "overhead_base": DEFAULT_OVERHEAD_BASE,
        "risk_reserve": DEFAULT_RISK_RESERVE,
    }


# ─── DEFAULT FUEL ECONOMY ────────────────────────────────────────

def get_default_fuel_economy(make: str, model: str, engine_cc: int = 0) -> float:
    """
    Return default fuel economy based on make/model/engine.
    Matches the frontend and api/routes/mileage.py implementation.
    """
    make = make.lower() if make else 'toyota'
    model = model.lower() if model else 'axio'
    
    # Toyota
    if make == 'toyota':
        if model in ['axio', 'corolla', 'premio', 'allion', 'vitz']:
            return 16
        elif model in ['camry', 'rav4']:
            return 13
        elif model in ['hilux', 'fortuner']:
            return 11
        elif model == 'land cruiser':
            return 8
        elif model == 'prado':
            return 10
        else:
            return 14
    
    # Honda
    elif make == 'honda':
        if model in ['fit', 'civic']:
            return 15
        elif model in ['accord', 'cr-v', 'hr-v']:
            return 12
        else:
            return 13
    
    # Nissan
    elif make == 'nissan':
        if model in ['note', 'sunny']:
            return 15
        elif model in ['x-trail', 'qashqai']:
            return 13
        elif model == 'patrol':
            return 8
        else:
            return 13
    
    # Mercedes
    elif make in ['mercedes-benz', 'mercedes']:
        if model in ['c-class', 'gla']:
            return 13
        elif model in ['e-class', 'gle']:
            return 11
        else:
            return 12
    
    # BMW
    elif make == 'bmw':
        if model in ['1 series', '3 series']:
            return 13
        elif model in ['5 series', 'x3', 'x5']:
            return 11
        else:
            return 12
    
    # Default based on engine size
    elif engine_cc:
        if engine_cc <= 1300:
            return 18
        elif engine_cc <= 1800:
            return 15
        elif engine_cc <= 2500:
            return 12
        else:
            return 9
    
    # Default fallback
    return 13


# ─── CORE CALCULATION FUNCTION ──────────────────────────────────

def calculate_mileage_rate(
    vehicle_type: str = "sedan",
    usage: str = "business",
    region: str = "nairobi",
    road_condition: str = "mixed",
    purpose: str = "mileage_rate_report",
    fuel_price: Optional[float] = None,
    km_per_liter: Optional[float] = None,
    maintenance_base: Optional[float] = None,
    depreciation_base: Optional[float] = None,
    insurance_base: Optional[float] = None,
    overhead_base: Optional[float] = None,
    risk_reserve: Optional[float] = None,
    monthly_km: int = 2000,
    yearly_km: int = 24000,
    make: str = "Toyota",
    model: str = "Axio",
    purchase_price: Optional[float] = None,
    vehicle_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calculate a comprehensive mileage rate report.
    Aligned with frontend and api/routes/mileage.py.
    
    Args:
        vehicle_type: sedan, suv, pickup, truck, van, luxury, motorcycle
        usage: business, personal, commercial, fleet, uber, delivery
        region: nairobi, mombasa, kisumu, nakuru, eldoret, rural, other
        road_condition: highway, mixed, urban, rural, offroad, excellent, good, fair, poor
        purpose: mileage_rate_report, vehicle_running_cost_analysis, fleet_running_cost_analysis
        fuel_price: override default
        km_per_liter: override default
        maintenance_base: override default
        depreciation_base: override default
        insurance_base: override default
        overhead_base: override default
        risk_reserve: override default
        monthly_km: distance driven per month
        yearly_km: distance driven per year
        make: vehicle make (for auto-fill)
        model: vehicle model (for auto-fill)
        purchase_price: override purchase price
        vehicle_data: full vehicle data dict (for auto-fill)
    
    Returns:
        Dictionary with cost_per_km, projections, breakdown, and purpose-specific adjustments.
    """
    # ─── Get System Settings ──────────────────────────────────
    settings = get_system_settings()
    
    fuel_price = fuel_price or settings.get("fuel_price", DEFAULT_FUEL_PRICE)
    km_per_liter = km_per_liter or settings.get("km_per_liter", DEFAULT_KM_PER_LITER)
    maintenance_base = maintenance_base or settings.get("maintenance_base", DEFAULT_MAINTENANCE_BASE)
    depreciation_base = depreciation_base or settings.get("depreciation_base", DEFAULT_DEPRECIATION_BASE)
    insurance_base = insurance_base or settings.get("insurance_base", DEFAULT_INSURANCE_BASE)
    overhead_base = overhead_base or settings.get("overhead_base", DEFAULT_OVERHEAD_BASE)
    risk_reserve = risk_reserve or settings.get("risk_reserve", DEFAULT_RISK_RESERVE)
    
    # ─── Auto-fill from vehicle database ──────────────────────
    vehicle_key = f"{make} {model}"
    db_vehicle = VEHICLE_DATABASE.get(vehicle_key, {})
    
    if db_vehicle:
        if not purchase_price:
            purchase_price = db_vehicle.get('basePrice', 2500000)
        if not km_per_liter or km_per_liter == DEFAULT_KM_PER_LITER:
            km_per_liter = db_vehicle.get('economy', DEFAULT_KM_PER_LITER)
        # Use database values as fallbacks for components
        if maintenance_base == DEFAULT_MAINTENANCE_BASE:
            maintenance_base = (db_vehicle.get('service', 35000) / 20000)  # Convert to per km
        if insurance_base == DEFAULT_INSURANCE_BASE:
            insurance_base = (db_vehicle.get('insurance', 65000) / 20000)
    else:
        if not purchase_price:
            purchase_price = 2500000
    
    # ─── Get fuel economy ──────────────────────────────────────
    if not km_per_liter or km_per_liter == DEFAULT_KM_PER_LITER:
        km_per_liter = get_default_fuel_economy(make, model, 0)
    
    # ─── Fuel cost per km ──────────────────────────────────────
    fuel_cost_per_km = fuel_price / km_per_liter if km_per_liter > 0 else 0
    
    # ─── Base cost per km ──────────────────────────────────────
    base_cost_per_km = (
        fuel_cost_per_km
        + maintenance_base
        + depreciation_base
        + insurance_base
        + overhead_base
    )
    
    # ─── Apply multipliers ──────────────────────────────────────
    vehicle_factor = VEHICLE_MULTIPLIER.get(vehicle_type.lower(), 1.0)
    usage_factor = USAGE_MULTIPLIER.get(usage.lower(), 1.0)
    region_factor = REGION_MULTIPLIER.get(region.lower(), 1.0)
    road_factor = ROAD_CONDITION.get(road_condition.lower(), 1.0)
    purpose_factor = PURPOSE_FACTORS.get(purpose, 1.0)
    
    # ─── Apply journey purpose if provided ─────────────────────
    journey_purpose = JOURNEY_PURPOSE.get(usage.lower(), 1.0)
    
    # ─── Final cost per KM ──────────────────────────────────────
    cost_per_km = (
        base_cost_per_km
        * vehicle_factor
        * usage_factor
        * region_factor
        * road_factor
        * purpose_factor
        * journey_purpose
    )
    cost_per_km = round(cost_per_km, 2)
    
    # ─── Apply risk reserve ─────────────────────────────────────
    risk_reserve_amount = cost_per_km * risk_reserve
    cost_with_reserve = cost_per_km + risk_reserve_amount
    
    # ─── Projections ────────────────────────────────────────────
    monthly_cost = round(cost_with_reserve * monthly_km)
    yearly_cost = round(cost_with_reserve * yearly_km)
    
    # ─── Generate report ID ────────────────────────────────────
    report_id = f"MR-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
    # ─── Build result ──────────────────────────────────────────
    result = {
        "report_id": report_id,
        "cost_per_km": cost_with_reserve,
        "cost_per_month": monthly_cost,
        "cost_per_year": yearly_cost,
        "monthly_km": monthly_km,
        "yearly_km": yearly_km,
        "fuel_cost_per_km": round(fuel_cost_per_km, 2),
        "risk_reserve_percent": round(risk_reserve * 100, 1),
        "breakdown": {
            "base_cost_per_km": round(base_cost_per_km, 2),
            "vehicle_factor": vehicle_factor,
            "usage_factor": usage_factor,
            "region_factor": region_factor,
            "road_factor": road_factor,
            "purpose_factor": purpose_factor,
            "journey_purpose": journey_purpose,
            "risk_reserve": risk_reserve,
        },
        "components": {
            "fuel": round(fuel_cost_per_km, 2),
            "maintenance": maintenance_base,
            "depreciation": depreciation_base,
            "insurance": insurance_base,
            "overhead": overhead_base,
            "risk_reserve": round(risk_reserve_amount, 2),
        },
        "inputs": {
            "vehicle_type": vehicle_type,
            "make": make,
            "model": model,
            "vehicle_key": vehicle_key,
            "purchase_price": purchase_price,
            "usage": usage,
            "region": region,
            "road_condition": road_condition,
            "purpose": purpose,
            "fuel_price": fuel_price,
            "km_per_liter": km_per_liter,
            "monthly_km": monthly_km,
            "yearly_km": yearly_km,
        },
        "vehicle_data": db_vehicle if db_vehicle else None,
        "in_database": bool(db_vehicle),
        "purpose": purpose,
        "generated_at": datetime.now().isoformat(),
    }
    
    return result


# ─── QUICK ESTIMATE ─────────────────────────────────────────────

def quick_mileage_estimate(vehicle_type: str) -> float:
    """
    Simple estimate for instant UI display.
    Returns cost per km as float.
    """
    base = 35.0  # KES per km baseline (Kenya average)
    factor = VEHICLE_MULTIPLIER.get(vehicle_type.lower(), 1.0)
    return round(base * factor, 2)


def quick_estimate_with_usage(vehicle_type: str, usage: str) -> float:
    """
    Quick estimate with usage factor.
    """
    base = 35.0
    vehicle_factor = VEHICLE_MULTIPLIER.get(vehicle_type.lower(), 1.0)
    usage_factor = USAGE_MULTIPLIER.get(usage.lower(), 1.0)
    return round(base * vehicle_factor * usage_factor, 2)


# ─── GET MILEAGE PURPOSE FEE ────────────────────────────────────

def get_mileage_purpose_fee(purpose: str) -> float:
    """
    Get the fee for a specific mileage purpose from system_settings.
    """
    # In production, this would query the database.
    # For now, return default fee.
    return 1500.0  # Default KES


# ─── UNIFIED ENTRY POINT ────────────────────────────────────────

def run_mileage_rate(
    vehicle_type: str,
    usage: str,
    region: str,
    road_condition: str,
    purpose: str = "mileage_rate_report",
    monthly_km: int = 2000,
    yearly_km: int = 24000,
    make: str = "Toyota",
    model: str = "Axio",
    **kwargs
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
        make=make,
        model=model,
        **kwargs
    )
    return result


# ─── COMPARE VEHICLES ───────────────────────────────────────────

def compare_vehicles(
    vehicle1: Dict[str, Any],
    vehicle2: Dict[str, Any],
    annual_km: int = 20000,
    fuel_type: str = "petrol"
) -> Dict[str, Any]:
    """
    Compare mileage rates between two vehicles.
    Matches the comparison endpoint in api/routes/mileage.py.
    """
    # Get fuel price
    fuel_prices = DEFAULT_FUEL_PRICES
    fuel_price = fuel_prices.get(fuel_type, DEFAULT_FUEL_PRICE)
    
    # Calculate rates
    v1_params = {
        'make': vehicle1.get('make', 'Toyota'),
        'model': vehicle1.get('model', 'Axio'),
        'vehicle_type': vehicle1.get('vehicle_type', 'sedan'),
        'usage': vehicle1.get('usage', 'business'),
        'region': vehicle1.get('region', 'nairobi'),
        'road_condition': vehicle1.get('road_condition', 'mixed'),
        'annual_km': annual_km,
        'fuel_price': fuel_price,
    }
    
    v2_params = {
        'make': vehicle2.get('make', 'Toyota'),
        'model': vehicle2.get('model', 'Prado'),
        'vehicle_type': vehicle2.get('vehicle_type', 'suv'),
        'usage': vehicle2.get('usage', 'business'),
        'region': vehicle2.get('region', 'nairobi'),
        'road_condition': vehicle2.get('road_condition', 'mixed'),
        'annual_km': annual_km,
        'fuel_price': fuel_price,
    }
    
    result1 = calculate_mileage_rate(**v1_params)
    result2 = calculate_mileage_rate(**v2_params)
    
    diff_percent = ((result2['cost_per_km'] - result1['cost_per_km']) / result1['cost_per_km'] * 100)
    
    return {
        'vehicle1': {
            'name': f"{v1_params['make']} {v1_params['model']}",
            'rate': result1['cost_per_km'],
            'annual_cost': result1['cost_per_year'],
        },
        'vehicle2': {
            'name': f"{v2_params['make']} {v2_params['model']}",
            'rate': result2['cost_per_km'],
            'annual_cost': result2['cost_per_year'],
        },
        'comparison': {
            'diff_percent': round(diff_percent, 1),
            'diff_amount': round(abs(result2['cost_per_km'] - result1['cost_per_km']), 2),
            'cheaper': f"{v1_params['make']} {v1_params['model']}" if result1['cost_per_km'] < result2['cost_per_km'] else f"{v2_params['make']} {v2_params['model']}"
        }
    }


# ─── GET VEHICLE LIST ───────────────────────────────────────────

def get_vehicle_list() -> Dict[str, List[str]]:
    """
    Get all vehicles grouped by make.
    Matches the vehicle-list endpoint in api/routes/mileage.py.
    """
    vehicles = {}
    for key in VEHICLE_DATABASE.keys():
        make, model = key.split(' ', 1)
        if make not in vehicles:
            vehicles[make] = []
        vehicles[make].append(model)
    return vehicles


# ─── GET VEHICLE DATA ──────────────────────────────────────────

def get_vehicle_data(make: str, model: str) -> Dict[str, Any]:
    """
    Get vehicle data from database.
    Matches the vehicle-data endpoint in api/routes/mileage.py.
    """
    vehicle_key = f"{make} {model}"
    if vehicle_key in VEHICLE_DATABASE:
        data = VEHICLE_DATABASE[vehicle_key].copy()
        data['in_database'] = True
        data['key'] = vehicle_key
        data['suggested_economy'] = get_default_fuel_economy(make, model, 0)
        return data
    else:
        return {
            'in_database': False,
            'basePrice': 2500000,
            'insurance': 65000,
            'service': 35000,
            'repairs': 25000,
            'tyres': 40000,
            'licence': 15000,
            'finance': 50000,
            'suggested_economy': get_default_fuel_economy(make, model, 0)
        }


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    # Full mileage rate report
    result = calculate_mileage_rate(
        vehicle_type="suv",
        usage="business",
        region="nairobi",
        road_condition="mixed",
        purpose="mileage_rate_report",
        monthly_km=2500,
        yearly_km=30000,
        make="Toyota",
        model="RAV4"
    )

    print("=" * 60)
    print("MILEAGE RATE REPORT")
    print("=" * 60)
    print(f"Report ID: {result['report_id']}")
    print(f"Vehicle: {result['inputs']['make']} {result['inputs']['model']}")
    print(f"In Database: {'✅' if result['in_database'] else '❌'}")
    print(f"\nCost per KM: KES {result['cost_per_km']:.2f}")
    print(f"Monthly ({result['monthly_km']:,}km): KES {result['cost_per_month']:,}")
    print(f"Yearly ({result['yearly_km']:,}km): KES {result['cost_per_year']:,}")
    print(f"Fuel Cost/KM: KES {result['fuel_cost_per_km']:.2f}")
    print(f"Risk Reserve: {result['risk_reserve_percent']}%")
    
    print("\n" + "-" * 60)
    print("Breakdown:")
    for key, val in result["breakdown"].items():
        print(f"  {key}: {val}")
    
    print("\n" + "-" * 60)
    print("Components (KES per km):")
    for key, val in result["components"].items():
        print(f"  {key}: {val:.2f}")
    
    print("\n" + "-" * 60)
    print("Inputs:")
    for key, val in result["inputs"].items():
        print(f"  {key}: {val}")
    
    # Quick estimate
    print("\n" + "=" * 60)
    print("QUICK ESTIMATE")
    print("=" * 60)
    print(f"SUV: KES {quick_mileage_estimate('suv')}/km")
    print(f"SUV (Business): KES {quick_estimate_with_usage('suv', 'business')}/km")
    
    # Compare vehicles
    print("\n" + "=" * 60)
    print("VEHICLE COMPARISON")
    print("=" * 60)
    comparison = compare_vehicles(
        {'make': 'Toyota', 'model': 'Axio', 'vehicle_type': 'sedan'},
        {'make': 'Toyota', 'model': 'Prado', 'vehicle_type': 'suv'},
        annual_km=20000
    )
    print(f"{comparison['vehicle1']['name']}: KES {comparison['vehicle1']['rate']:.2f}/km")
    print(f"{comparison['vehicle2']['name']}: KES {comparison['vehicle2']['rate']:.2f}/km")
    print(f"Difference: {comparison['comparison']['diff_percent']}%")
    print(f"Cheaper: {comparison['comparison']['cheaper']}")
