# api/routes/mileage.py - Mileage & Odometer Routes with Rate Engine
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import re

from services.supabase_client import get_supabase
from services.vin_validator import vin_validator
from services.carapi_service import get_carapi_service
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

# Create blueprint
mileage_bp = Blueprint('mileage', __name__)

# ─── VEHICLE DATABASE ────────────────────────────────────────────

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

# ─── DEFAULT FUEL PRICES ────────────────────────────────────────

DEFAULT_FUEL_PRICES = {
    'petrol': 199.15,
    'diesel': 185.00,
    'hybrid': 199.15,
    'lpg': 120.00,
    'electric': 20.00
}

# ─── CORE CALCULATION FUNCTION ──────────────────────────────────

def calculate_mileage_rate(vehicle_data: dict) -> dict:
    """
    Calculate mileage reimbursement rate based on total cost of ownership.
    Returns rate per km and breakdown.
    
    Args:
        vehicle_data: Dictionary with vehicle parameters
        
    Returns:
        Dictionary with calculated rates and breakdown
    """
    # Extract vehicle data with defaults
    purchase_price = vehicle_data.get('purchase_price', 2500000)
    residual_value = vehicle_data.get('residual_value', purchase_price * 0.3)
    annual_km = vehicle_data.get('annual_km', 20000)
    
    # Get fuel economy - use provided or default from vehicle database
    fuel_economy = vehicle_data.get('fuel_economy')
    if not fuel_economy:
        make = vehicle_data.get('make', 'Toyota')
        model = vehicle_data.get('model', 'Axio')
        engine_cc = vehicle_data.get('engine_capacity', 1500)
        fuel_economy = get_default_fuel_economy(make, model, engine_cc)
    
    fuel_type = vehicle_data.get('fuel_type', 'petrol')
    
    # Operating costs
    insurance = vehicle_data.get('insurance_cost', 65000)
    service = vehicle_data.get('service_cost', 35000)
    repairs = vehicle_data.get('repair_cost', 25000)
    tyres = vehicle_data.get('tyre_cost', 40000)
    tyre_life = vehicle_data.get('tyre_life', 50000)
    licence = vehicle_data.get('licence_cost', 15000)
    finance = vehicle_data.get('finance_cost', 50000)
    dep_rate = vehicle_data.get('depreciation_rate', 0.125)
    risk_reserve = vehicle_data.get('risk_reserve', 0.05)
    
    # ─── Depreciation ──────────────────────────────────────────
    annual_depreciation = (purchase_price - residual_value) * dep_rate
    
    # ─── Fuel Cost ────────────────────────────────────────────
    fuel_prices = DEFAULT_FUEL_PRICES.copy()
    # Allow override from vehicle_data
    if vehicle_data.get('fuel_price'):
        fuel_prices[fuel_type] = vehicle_data.get('fuel_price')
    
    fuel_price = fuel_prices.get(fuel_type, 199.15)
    
    if fuel_type == 'electric':
        # Electric: ~0.5 kWh per km
        electricity_cost = vehicle_data.get('electricity_cost', 20)
        annual_fuel_cost = annual_km * (electricity_cost * 0.5)
    elif fuel_type == 'lpg':
        lpg_efficiency = vehicle_data.get('lpg_efficiency', 12)  # km/kg
        annual_fuel_cost = (annual_km / lpg_efficiency) * fuel_price
    else:
        annual_fuel_cost = (annual_km / fuel_economy) * fuel_price
    
    # ─── Tyre Cost (annualized) ──────────────────────────────
    annual_tyre_cost = (tyres / tyre_life) * annual_km
    
    # ─── Apply Factors ────────────────────────────────────────
    factors = {
        'journey_purpose': {
            'business': 1.0,
            'ngo': 0.95,
            'government': 0.90,
            'private': 1.0,
            'fleet': 0.92
        },
        'road_condition': {
            'highway': 0.85,
            'mixed': 1.0,
            'urban': 1.10,
            'rural': 0.95,
            'offroad': 1.25
        },
        'location': {
            'nairobi': 1.05,
            'mombasa': 1.02,
            'kisumu': 1.0,
            'nakuru': 0.98,
            'eldoret': 0.97,
            'rural': 0.92
        },
        'driver_behaviour': {
            'conservative': 0.90,
            'normal': 1.0,
            'aggressive': 1.12
        },
        'maintenance_quality': {
            'dealer': 1.15,
            'independent': 1.0,
            'poor': 1.30
        }
    }
    
    # Get factor values from vehicle_data
    purpose = vehicle_data.get('journey_purpose', 'business')
    road = vehicle_data.get('road_condition', 'mixed')
    location = vehicle_data.get('location', 'nairobi')
    driver = vehicle_data.get('driver_behaviour', 'normal')
    maintenance = vehicle_data.get('maintenance_quality', 'independent')
    
    # Calculate combined factor
    combined_factor = (
        factors['journey_purpose'].get(purpose, 1.0) *
        factors['road_condition'].get(road, 1.0) *
        factors['location'].get(location, 1.0) *
        factors['driver_behaviour'].get(driver, 1.0) *
        factors['maintenance_quality'].get(maintenance, 1.0)
    )
    
    # ─── Apply combined factor to variable costs ──────────────
    adjusted_fuel = annual_fuel_cost * combined_factor
    adjusted_tyre = annual_tyre_cost * combined_factor
    adjusted_service = service * combined_factor
    adjusted_repair = repairs * combined_factor
    
    # ─── Total Annual Cost ─────────────────────────────────────
    total_before_reserve = (
        annual_depreciation + adjusted_fuel + adjusted_tyre +
        adjusted_service + insurance + licence + adjusted_repair + finance
    )
    
    reserve_amount = total_before_reserve * risk_reserve
    total_annual_cost = total_before_reserve + reserve_amount
    
    # ─── Rates ─────────────────────────────────────────────────
    rate_per_km = total_annual_cost / annual_km
    rate_per_mile = rate_per_km * 1.60934
    
    # ─── Return Result ─────────────────────────────────────────
    return {
        'rate_per_km': round(rate_per_km, 2),
        'rate_per_mile': round(rate_per_mile, 2),
        'total_annual_cost': round(total_annual_cost, 2),
        'monthly_cost': round(total_annual_cost / 12, 2),
        'fuel_cost_per_year': round(adjusted_fuel, 2),
        'depreciation_per_year': round(annual_depreciation, 2),
        'risk_reserve_percent': round(risk_reserve * 100, 1),
        'risk_reserve_amount': round(reserve_amount, 2),
        'combined_factor': round(combined_factor, 2),
        'breakdown': {
            'depreciation': round(annual_depreciation, 2),
            'fuel': round(adjusted_fuel, 2),
            'service': round(adjusted_service, 2),
            'tyres': round(adjusted_tyre, 2),
            'insurance': round(insurance, 2),
            'licence': round(licence, 2),
            'repairs': round(adjusted_repair, 2),
            'finance': round(finance, 2),
            'risk_reserve': round(reserve_amount, 2)
        },
        'vehicle_data': {
            'make': vehicle_data.get('make', 'Toyota'),
            'model': vehicle_data.get('model', 'Axio'),
            'year': vehicle_data.get('year'),
            'fuel_type': fuel_type,
            'purchase_price': purchase_price,
            'fuel_economy': fuel_economy
        },
        'usage_factors': {
            'journey_purpose': purpose,
            'road_condition': road,
            'location': location,
            'driver_behaviour': driver,
            'maintenance_quality': maintenance
        },
        'timestamp': datetime.now().isoformat()
    }


def get_default_fuel_economy(make: str, model: str, engine_cc: int) -> float:
    """
    Return default fuel economy based on make/model/engine.
    
    Args:
        make: Vehicle make
        model: Vehicle model
        engine_cc: Engine capacity in CC
        
    Returns:
        Fuel economy in km/L
    """
    make = make.lower() if make else 'toyota'
    model = model.lower() if model else 'axio'
    
    # Toyota
    if make == 'toyota':
        if model in ['axio', 'corolla', 'premio', 'allion']:
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
    elif make == 'mercedes-benz' or make == 'mercedes':
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


# ─── HELPER FUNCTIONS ────────────────────────────────────────────

def get_vehicle_from_database(make: str, model: str) -> dict:
    """Get vehicle data from database"""
    vehicle_key = f"{make} {model}"
    return VEHICLE_DATABASE.get(vehicle_key, {})


def get_all_vehicles() -> dict:
    """Get all vehicles grouped by make"""
    vehicles = {}
    for key in VEHICLE_DATABASE.keys():
        make, model = key.split(' ', 1)
        if make not in vehicles:
            vehicles[make] = []
        vehicles[make].append(model)
    return vehicles


# ─── ROUTES ──────────────────────────────────────────────────────

@mileage_bp.route('/calculate-rate', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def calculate_rate():
    """
    Calculate mileage rate based on vehicle parameters
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        if not data.get('make') or not data.get('model'):
            return jsonify({
                'success': False,
                'error': 'make and model are required'
            }), 400
        
        # If VIN provided, try to auto-fill from CarAPI
        vin = data.get('vin')
        if vin:
            vin = vin.upper().strip()
            if vin_validator.is_valid(vin):
                try:
                    carapi = get_carapi_service()
                    vin_data = carapi.decode_vin(vin)
                    if 'error' not in vin_data:
                        data['make'] = vin_data.get('make', data.get('make'))
                        data['model'] = vin_data.get('model', data.get('model'))
                        data['year'] = vin_data.get('year', data.get('year'))
                        data['engine_capacity'] = vin_data.get('engine_cc')
                        data['fuel_type'] = vin_data.get('fuel_type', data.get('fuel_type'))
                except Exception as e:
                    logger.warning(f"CarAPI lookup failed: {str(e)}")
        
        # Try to get vehicle data from database
        db_vehicle = get_vehicle_from_database(data['make'], data['model'])
        if db_vehicle:
            # Merge database values with provided data (provided takes precedence)
            for key, value in db_vehicle.items():
                if key not in data or data.get(key) is None:
                    # Map database keys to calculation keys
                    if key == 'basePrice':
                        data['purchase_price'] = value
                    elif key == 'economy':
                        data['fuel_economy'] = value
                    elif key == 'insurance':
                        data['insurance_cost'] = value
                    elif key == 'service':
                        data['service_cost'] = value
                    elif key == 'repairs':
                        data['repair_cost'] = value
                    elif key == 'tyres':
                        data['tyre_cost'] = value
                    elif key == 'licence':
                        data['licence_cost'] = value
                    elif key == 'finance':
                        data['finance_cost'] = value
        
        # Set defaults for missing values
        data.setdefault('purchase_price', 2500000)
        data.setdefault('residual_value', data['purchase_price'] * 0.3)
        data.setdefault('annual_km', 20000)
        data.setdefault('fuel_type', 'petrol')
        data.setdefault('insurance_cost', 65000)
        data.setdefault('service_cost', 35000)
        data.setdefault('repair_cost', 25000)
        data.setdefault('tyre_cost', 40000)
        data.setdefault('tyre_life', 50000)
        data.setdefault('licence_cost', 15000)
        data.setdefault('finance_cost', 50000)
        data.setdefault('depreciation_rate', 0.125)
        data.setdefault('risk_reserve', 0.05)
        data.setdefault('journey_purpose', 'business')
        data.setdefault('road_condition', 'mixed')
        data.setdefault('location', 'nairobi')
        data.setdefault('driver_behaviour', 'normal')
        data.setdefault('maintenance_quality', 'independent')
        
        # Calculate rate
        result = calculate_mileage_rate(data)
        
        # Save calculation to database if user is authenticated
        try:
            supabase = get_supabase()
            calc_data = {
                'user_id': request.user_id,
                'make': data.get('make'),
                'model': data.get('model'),
                'vin': data.get('vin'),
                'annual_km': data.get('annual_km', 20000),
                'fuel_type': data.get('fuel_type', 'petrol'),
                'mileage_rate': result['rate_per_km'],
                'total_annual_cost': result['total_annual_cost'],
                'parameters': data,
                'result': result,
                'calculated_at': datetime.now().isoformat()
            }
            supabase.save_mileage_calculation(calc_data)
        except Exception as e:
            logger.warning(f"Failed to save calculation: {str(e)}")
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Mileage rate calculated successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Calculate rate error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mileage_bp.route('/vehicle-data', methods=['POST'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_vehicle_data():
    """
    Get vehicle data from database (for auto-fill)
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('make') or not data.get('model'):
            return jsonify({
                'success': False,
                'error': 'make and model are required'
            }), 400
        
        make = data['make']
        model = data['model']
        vehicle_key = f"{make} {model}"
        
        if vehicle_key in VEHICLE_DATABASE:
            vehicle_data = VEHICLE_DATABASE[vehicle_key].copy()
            vehicle_data['in_database'] = True
            vehicle_data['key'] = vehicle_key
            vehicle_data['suggested_economy'] = get_default_fuel_economy(make, model, 0)
            
            return jsonify({
                'success': True,
                'data': vehicle_data,
                'message': 'Vehicle data found'
            }), 200
        else:
            # Return default data
            return jsonify({
                'success': True,
                'data': {
                    'in_database': False,
                    'basePrice': 2500000,
                    'insurance': 65000,
                    'service': 35000,
                    'repairs': 25000,
                    'tyres': 40000,
                    'licence': 15000,
                    'finance': 50000,
                    'suggested_economy': get_default_fuel_economy(make, model, 0)
                },
                'message': 'Vehicle not in database, using defaults'
            }), 200
        
    except Exception as e:
        logger.error(f"Get vehicle data error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mileage_bp.route('/vehicle-list', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_vehicle_list():
    """
    Get list of vehicles for dropdown
    """
    try:
        vehicles = get_all_vehicles()
        
        return jsonify({
            'success': True,
            'data': vehicles,
            'count': len(VEHICLE_DATABASE)
        }), 200
        
    except Exception as e:
        logger.error(f"Get vehicle list error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mileage_bp.route('/compare', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def compare_vehicles():
    """
    Compare mileage rates between two vehicles
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('vehicle1') or not data.get('vehicle2'):
            return jsonify({
                'success': False,
                'error': 'vehicle1 and vehicle2 are required'
            }), 400
        
        annual_km = data.get('annual_km', 20000)
        fuel_type = data.get('fuel_type', 'petrol')
        
        # Parse vehicle names
        v1_parts = data['vehicle1'].split(' ', 1)
        v2_parts = data['vehicle2'].split(' ', 1)
        
        vehicle1_data = {
            'make': v1_parts[0],
            'model': v1_parts[1] if len(v1_parts) > 1 else '',
            'annual_km': annual_km,
            'fuel_type': fuel_type
        }
        
        vehicle2_data = {
            'make': v2_parts[0],
            'model': v2_parts[1] if len(v2_parts) > 1 else '',
            'annual_km': annual_km,
            'fuel_type': fuel_type
        }
        
        result1 = calculate_mileage_rate(vehicle1_data)
        result2 = calculate_mileage_rate(vehicle2_data)
        
        diff_percent = ((result2['rate_per_km'] - result1['rate_per_km']) / result1['rate_per_km'] * 100)
        
        return jsonify({
            'success': True,
            'data': {
                'vehicle1': {
                    'name': data['vehicle1'],
                    'rate': result1['rate_per_km'],
                    'annual_cost': result1['total_annual_cost'],
                    'breakdown': result1['breakdown']
                },
                'vehicle2': {
                    'name': data['vehicle2'],
                    'rate': result2['rate_per_km'],
                    'annual_cost': result2['total_annual_cost'],
                    'breakdown': result2['breakdown']
                },
                'comparison': {
                    'diff_percent': round(diff_percent, 1),
                    'diff_amount': round(abs(result2['rate_per_km'] - result1['rate_per_km']), 2),
                    'savings_annual': round(abs(result2['total_annual_cost'] - result1['total_annual_cost']), 2),
                    'cheaper': data['vehicle1'] if result1['rate_per_km'] < result2['rate_per_km'] else data['vehicle2']
                }
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Compare vehicles error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mileage_bp.route('/fuel-prices', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_fuel_prices():
    """
    Get current fuel prices
    """
    try:
        # Get from database or use defaults
        supabase = get_supabase()
        prices = supabase.get_fuel_prices()
        
        if not prices:
            prices = DEFAULT_FUEL_PRICES
        
        return jsonify({
            'success': True,
            'data': prices,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Get fuel prices error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mileage_bp.route('/fuel-prices', methods=['PUT'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def update_fuel_prices():
    """
    Update fuel prices
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate prices
        for fuel, price in data.items():
            if fuel in DEFAULT_FUEL_PRICES:
                if not isinstance(price, (int, float)) or price <= 0:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid price for {fuel}'
                    }), 400
        
        # Save to database
        supabase = get_supabase()
        result = supabase.update_fuel_prices(data)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to update fuel prices')
            }), 500
        
        return jsonify({
            'success': True,
            'data': data,
            'message': 'Fuel prices updated successfully',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Update fuel prices error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ─── ORIGINAL MILEAGE RECORD ROUTES ────────────────────────────

@mileage_bp.route('/record', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def record_mileage():
    """
    Record a new mileage reading
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['vin', 'odometer_reading']
        missing = [f for f in required_fields if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        # Validate VIN
        vin = data['vin'].upper().strip()
        if not vin_validator.is_valid(vin):
            return jsonify({
                'success': False,
                'error': 'Invalid VIN format'
            }), 400
        
        # Validate odometer reading
        odometer = data['odometer_reading']
        if not isinstance(odometer, (int, float)) or odometer < 0:
            return jsonify({
                'success': False,
                'error': 'Odometer reading must be a positive number'
            }), 400
        
        # Save to Supabase
        supabase = get_supabase()
        
        # Check for previous reading
        previous = supabase.get_latest_mileage(vin)
        if previous:
            diff = odometer - previous.get('odometer_reading', 0)
            if diff < 0:
                return jsonify({
                    'success': False,
                    'error': f'Odometer reading ({odometer}) is less than previous reading ({previous.get("odometer_reading")})'
                }), 400
        
        result = supabase.save_mileage_record({
            'vin': vin,
            'user_id': request.user_id,
            'odometer_reading': odometer,
            'unit': data.get('unit', 'km'),
            'reading_date': data.get('reading_date', datetime.now().isoformat()),
            'reading_location': data.get('reading_location'),
            'notes': data.get('notes'),
            'image_url': data.get('image_url'),
            'verified_by': data.get('verified_by'),
            'verification_status': data.get('verification_status', 'pending'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        })
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to save mileage record')
            }), 500
        
        return jsonify({
            'success': True,
            'data': {
                'record_id': result.get('data', {}).get('id'),
                'vin': vin,
                'odometer_reading': odometer,
                'unit': data.get('unit', 'km'),
                'reading_date': data.get('reading_date', datetime.now().isoformat())
            },
            'message': 'Mileage recorded successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Record mileage error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/<record_id>', methods=['GET'])
@rate_limit(limit=50, per=60)
@require_auth
@log_request
def get_mileage_record(record_id):
    """
    Get mileage record by ID
    """
    try:
        supabase = get_supabase()
        result = supabase.get_mileage_record(record_id)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Mileage record not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Get mileage record error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/vehicle/<vin>', methods=['GET'])
@rate_limit(limit=50, per=60)
@require_auth
@log_request
def get_mileage_history(vin):
    """
    Get mileage history for a vehicle
    """
    try:
        vin = vin.upper().strip()
        
        supabase = get_supabase()
        results = supabase.get_mileage_history(vin)
        
        # Calculate statistics
        stats = {}
        if results:
            readings = [r.get('odometer_reading', 0) for r in results]
            stats = {
                'first_reading': results[-1].get('odometer_reading') if results else None,
                'latest_reading': results[0].get('odometer_reading') if results else None,
                'total_readings': len(results),
                'average_mileage': sum(readings) / len(readings) if readings else 0,
                'highest_reading': max(readings) if readings else 0,
                'lowest_reading': min(readings) if readings else 0
            }
        
        return jsonify({
            'success': True,
            'data': results,
            'stats': stats,
            'count': len(results)
        }), 200
        
    except Exception as e:
        logger.error(f"Get mileage history error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/<record_id>/verify', methods=['PUT'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def verify_mileage(record_id):
    """
    Verify a mileage record
    """
    try:
        data = request.get_json()
        
        if not data or 'verified_by' not in data:
            return jsonify({
                'success': False,
                'error': 'verified_by is required'
            }), 400
        
        supabase = get_supabase()
        result = supabase.verify_mileage_record(
            record_id,
            data['verified_by'],
            data.get('notes', '')
        )
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to verify mileage record')
            }), 500
        
        return jsonify({
            'success': True,
            'data': {
                'record_id': record_id,
                'verified_by': data['verified_by'],
                'verification_status': 'verified',
                'verified_at': datetime.now().isoformat()
            },
            'message': 'Mileage record verified successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Verify mileage error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/<record_id>', methods=['DELETE'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def delete_mileage_record(record_id):
    """
    Delete a mileage record
    """
    try:
        supabase = get_supabase()
        result = supabase.delete_mileage_record(record_id)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to delete mileage record')
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Mileage record deleted successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Delete mileage record error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/check-mileage/<vin>', methods=['GET'])
@rate_limit(limit=30, per=60)
@log_request
def check_mileage_consistency(vin):
    """
    Check mileage consistency for a vehicle
    """
    try:
        vin = vin.upper().strip()
        
        if not vin_validator.is_valid(vin):
            return jsonify({
                'success': False,
                'error': 'Invalid VIN format'
            }), 400
        
        supabase = get_supabase()
        results = supabase.get_mileage_history(vin)
        
        if len(results) < 2:
            return jsonify({
                'success': True,
                'data': {
                    'vin': vin,
                    'has_enough_data': False,
                    'message': 'Not enough mileage records for consistency check'
                }
            }), 200
        
        inconsistencies = []
        warnings = []
        results.sort(key=lambda x: x.get('reading_date', ''))
        
        for i in range(1, len(results)):
            current = results[i]
            previous = results[i-1]
            
            current_reading = current.get('odometer_reading', 0)
            previous_reading = previous.get('odometer_reading', 0)
            diff = current_reading - previous_reading
            
            if diff < 0:
                inconsistencies.append({
                    'date': current.get('reading_date'),
                    'reading': current_reading,
                    'previous_reading': previous_reading,
                    'difference': diff,
                    'issue': 'Odometer rolled back'
                })
            
            try:
                current_date = datetime.fromisoformat(current.get('reading_date', ''))
                previous_date = datetime.fromisoformat(previous.get('reading_date', ''))
                days = (current_date - previous_date).days
                
                if days > 0:
                    daily_mileage = diff / days
                    yearly_mileage = daily_mileage * 365
                    
                    if yearly_mileage > 100000:
                        warnings.append({
                            'date': current.get('reading_date'),
                            'reading': current_reading,
                            'yearly_mileage': round(yearly_mileage),
                            'issue': 'Unrealistically high mileage'
                        })
            except:
                pass
        
        status = 'consistent'
        if inconsistencies:
            status = 'inconsistent'
        elif warnings:
            status = 'warning'
        
        return jsonify({
            'success': True,
            'data': {
                'vin': vin,
                'status': status,
                'has_enough_data': True,
                'total_readings': len(results),
                'latest_reading': results[-1].get('odometer_reading'),
                'earliest_reading': results[0].get('odometer_reading'),
                'inconsistencies': inconsistencies,
                'warnings': warnings,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Check mileage consistency error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/stats', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_mileage_stats():
    """
    Get mileage statistics
    """
    try:
        supabase = get_supabase()
        stats = supabase.get_mileage_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Get mileage stats error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
