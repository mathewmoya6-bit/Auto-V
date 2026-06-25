# backend/services/instant_check.py
# AUTO-V Instant Value Check - Flask Service
# AI Valuation Engine for Cars and Motorcycles

from flask import Blueprint, request, jsonify
from datetime import datetime

# ─── Blueprint Setup ───────────────────────────────────────────────
instant_check_bp = Blueprint('instant_check', __name__, url_prefix='/instant-check')

# ============================================================
# AI VALUATION ENGINE DATA
# ============================================================

# 1. Base Market Prices (KES) - CARS
CAR_BASE_PRICES = {
    'Toyota': 2800000,
    'Nissan': 2300000,
    'BMW': 4500000,
    'Mercedes': 5000000,
    'Honda': 2500000,
    'Mazda': 2200000,
    'Volkswagen': 2400000,
    'Mitsubishi': 2100000,
    'Subaru': 2600000,
    'Ford': 2100000,
    'Other': 2000000
}

# 2. Base Market Prices (KES) - BIKES
BIKE_BASE_PRICES = {
    'Honda Bike': 350000,
    'Yamaha': 380000,
    'Suzuki': 320000,
    'Kawasaki': 450000,
    'TVS': 200000,
    'Bajaj': 180000,
    'Hero': 160000,
    'Royal Enfield': 600000,
    'KTM': 500000,
    'Other Bike': 250000
}

# 3. Consolidated Base Prices
BASE_PRICES = {**CAR_BASE_PRICES, **BIKE_BASE_PRICES}

# 4. Model Multipliers (Cars)
CAR_MODEL_MULTIPLIERS = {
    # Toyota
    'land cruiser': 1.45,
    'prado': 1.35,
    'hilux': 1.20,
    'corolla': 0.90,
    'axio': 0.90,
    'fielder': 0.95,
    'voxy': 1.05,
    'noah': 1.05,
    'hiace': 1.10,
    # Nissan
    'x-trail': 1.15,
    'patrol': 1.30,
    'navara': 1.10,
    'note': 0.80,
    # BMW
    'x5': 1.25,
    'x3': 1.15,
    '3 series': 1.10,
    # Mercedes
    'c-class': 1.10,
    'e-class': 1.25,
    'g-class': 1.50,
    # Honda
    'cr-v': 1.15,
    'accord': 1.10,
    'fit': 0.85,
    # Mazda
    'cx-5': 1.15,
    'demio': 0.85,
    # Subaru
    'forester': 1.10,
    'outback': 1.15,
    'legacy': 1.10
}

# 5. Model Multipliers (Bikes)
BIKE_MODEL_MULTIPLIERS = {
    # Honda
    'cbr': 1.20,
    'cb500': 1.10,
    'africa twin': 1.40,
    # Yamaha
    'r1': 1.20,
    'r6': 1.10,
    'mt-07': 1.00,
    'tenere': 1.25,
    # Suzuki
    'gsx-r': 1.15,
    'v-strom': 1.10,
    # Kawasaki
    'ninja': 1.20,
    'z900': 1.15,
    'versys': 1.10,
    # Royal Enfield
    'classic 350': 1.00,
    'himalayan': 1.10,
    'continental gt': 1.00,
    # KTM
    'duke': 1.05,
    'rc': 1.10,
    'adventure': 1.15,
    # Bajaj
    'pulsar': 1.00,
    'dominor': 1.05
}

# 6. Consolidated Model Multipliers
MODEL_MULTIPLIERS = {**CAR_MODEL_MULTIPLIERS, **BIKE_MODEL_MULTIPLIERS}

# 7. Factor Tables (Shared across all vehicles)
CONDITION_FACTORS = {
    'Excellent': 1.15,
    'Good': 1.0,
    'Fair': 0.85,
    'Poor': 0.65
}

ACCIDENT_FACTORS = {
    'None': 1.0,
    'Minor': 0.9,
    'Major': 0.65,
    'WriteOff': 0.4
}

LOCATION_FACTORS = {
    'Nairobi': 1.10,
    'Mombasa': 1.05,
    'Kisumu': 0.95,
    'Nakuru': 0.95,
    'Eldoret': 0.95,
    'Thika': 1.00,
    'Malindi': 0.90,
    'Other': 1.00
}

FUEL_FACTORS = {
    'Petrol': 1.0,
    'Diesel': 0.95,
    'Hybrid': 1.12,
    'Electric': 1.15
}

TRANSMISSION_FACTORS = {
    'Automatic': 1.05,
    'Manual': 1.0,
    'CVT': 1.08
}

USAGE_FACTORS = {
    'Personal': 1.0,
    'Commercial': 0.85
}

# 8. Ownership History Factor
def get_ownership_factor(owners):
    if owners == 0:      return 1.05  # Brand new
    if owners == 1:      return 1.00  # One previous owner
    if owners <= 3:      return 0.90  # 2-3 owners
    if owners <= 5:      return 0.80  # 4-5 owners
    return 0.65                         # 5+ owners

# ============================================================
# ROUTES
# ============================================================

@instant_check_bp.route('/', methods=['GET'])
def root():
    return jsonify({
        "service": "AUTO-V Instant Value Check",
        "status": "online",
        "supports": ["Cars", "Motorcycles"]
    })

@instant_check_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Instant Value Check",
        "timestamp": datetime.now().isoformat()
    })

@instant_check_bp.route('/valuate', methods=['POST'])
def calculate_instant_value():
    """
    AI-powered market value estimate for Cars and Motorcycles.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Extract required fields
        make = data.get('make')
        model = data.get('model')
        year = data.get('year')
        mileage = data.get('mileage')
        fuel_type = data.get('fuel_type')
        transmission = data.get('transmission')
        condition = data.get('condition')
        accident_history = data.get('accident_history')
        location = data.get('location')
        previous_owners = data.get('previous_owners', 0)
        usage_type = data.get('usage_type', 'Personal')
        vehicle_type = data.get('vehicle_type', 'Car')

        # Validate required fields
        if not all([make, model, year, mileage, fuel_type, transmission, condition, accident_history, location]):
            return jsonify({"success": False, "error": "Missing required parameters"}), 400

        # Type validation
        try:
            year = int(year)
            mileage = int(mileage)
            previous_owners = int(previous_owners)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Year, mileage, and previous_owners must be integers"}), 400

        # Range validation
        current_year = datetime.now().year
        if year < 1990 or year > current_year + 1:
            return jsonify({
                "success": False,
                "error": f"Invalid year: {year}. Must be between 1990 and {current_year + 1}"
            }), 400
        
        if mileage < 0:
            return jsonify({"success": False, "error": "Mileage cannot be negative"}), 400

        # Determine Base Price
        base_price_key = make
        if vehicle_type.lower() == "bike" and "Bike" not in base_price_key:
            base_price_key = f"{make} Bike"
        
        value = BASE_PRICES.get(base_price_key, 2000000)

        # Apply Model Multiplier
        model_key = model.lower().strip()
        model_multiplier = MODEL_MULTIPLIERS.get(model_key, 1.0)
        value = value * model_multiplier

        # Age Factor
        age = max(0, current_year - year)
        age_factor = max(0.35, min(1.0, 1 - (age * 0.07)))

        # Mileage Factor
        mileage_factor = max(0.45, min(1.0, 1 - (mileage / 300000)))

        # Condition Factor
        condition_factor = CONDITION_FACTORS.get(condition, 1.0)

        # Accident Factor
        accident_factor = ACCIDENT_FACTORS.get(accident_history, 1.0)

        # Location Factor
        location_factor = LOCATION_FACTORS.get(location, 1.0)

        # Fuel Type Factor
        fuel_factor = FUEL_FACTORS.get(fuel_type, 1.0)

        # Transmission Factor
        transmission_factor = TRANSMISSION_FACTORS.get(transmission, 1.0)

        # Usage Factor
        usage_factor = USAGE_FACTORS.get(usage_type, 1.0)

        # Ownership History Factor
        ownership_factor = get_ownership_factor(previous_owners)

        # Final Calculation
        final_value = (
            value
            * age_factor
            * mileage_factor
            * condition_factor
            * accident_factor
            * location_factor
            * fuel_factor
            * transmission_factor
            * usage_factor
            * ownership_factor
        )

        # Round to nearest 1,000 KES
        final_value = round(final_value / 1000) * 1000

        # Enforce absolute min and max
        final_value = max(150000, min(final_value, 8000000))

        return jsonify({
            "success": True,
            "value": int(final_value),
            "breakdown": {
                "base_price": int(value),
                "model_multiplier": round(model_multiplier, 2),
                "age_factor": round(age_factor, 2),
                "mileage_factor": round(mileage_factor, 2),
                "condition_factor": round(condition_factor, 2),
                "accident_factor": round(accident_factor, 2),
                "location_factor": round(location_factor, 2),
                "fuel_factor": round(fuel_factor, 2),
                "transmission_factor": round(transmission_factor, 2),
                "usage_factor": round(usage_factor, 2),
                "ownership_factor": round(ownership_factor, 2)
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Valuation engine error: {str(e)}"}), 500
