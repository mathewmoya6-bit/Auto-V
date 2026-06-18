import logging
from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from services.mileage_engine import calculate_mileage_rate
from api.auth_middleware import require_auth

logger = logging.getLogger(__name__)
mileage_bp = Blueprint('mileage', __name__)

@mileage_bp.route('/calculate', methods=['POST'])
@require_auth
def calculate(user):
    data = request.get_json()
    required = ['make', 'model', 'year', 'fuel_type', 'annual_km', 'purchase_price']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    vehicle_data = {
        'make': data.get('make'),
        'model': data.get('model'),
        'year': int(data.get('year')),
        'fuel_type': data.get('fuel_type'),
        'transmission': data.get('transmission', 'automatic'),
        'engine_capacity': data.get('engine_capacity', 1500),
        'purchase_price': float(data.get('purchase_price')),
        'residual_value': float(data.get('residual_value', data.get('purchase_price') * 0.3)),
        'annual_km': float(data.get('annual_km')),
        'fuel_economy': data.get('fuel_economy'),
        'insurance_cost': float(data.get('insurance_cost', 65000)),
        'service_cost': float(data.get('service_cost', 35000)),
        'repair_cost': float(data.get('repair_cost', 25000)),
        'tyre_cost': float(data.get('tyre_cost', 40000)),
        'tyre_life': float(data.get('tyre_life', 50000)),
        'licence_cost': float(data.get('licence_cost', 15000)),
        'finance_cost': float(data.get('finance_cost', 50000)),
        'depreciation_rate': float(data.get('depreciation_rate', 12.5)) / 100,
        'risk_reserve': float(data.get('risk_reserve', 5)) / 100,
        'journey_purpose': data.get('journey_purpose', 'business'),
        'road_condition': data.get('road_condition', 'mixed'),
        'location': data.get('location', 'nairobi'),
        'driver_behaviour': data.get('driver_behaviour', 'normal'),
        'maintenance_quality': data.get('maintenance_quality', 'independent')
    }

    result = calculate_mileage_rate(vehicle_data)
    return jsonify(result), 200

@mileage_bp.route('/claims', methods=['POST'])
@require_auth
def submit_claim(user):
    data = request.get_json()
    required = ['trip_date', 'start_location', 'end_location', 'distance_km', 'vehicle_category']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    supabase = get_supabase()
    # Get rate
    rate_resp = supabase.table('mileage_rates')\
        .select('rate_per_km')\
        .eq('vehicle_category', data['vehicle_category'])\
        .eq('is_active', True)\
        .execute()
    if not rate_resp.data:
        return jsonify({'error': 'No active rate for this category'}), 400
    rate_per_km = rate_resp.data[0]['rate_per_km']

    claim_amount = float(data['distance_km']) * rate_per_km
    claim_data = {
        'user_id': user.id,
        'vehicle_category': data['vehicle_category'],
        'start_location': data['start_location'],
        'end_location': data['end_location'],
        'distance_km': float(data['distance_km']),
        'rate_per_km': rate_per_km,
        'claim_amount': claim_amount,
        'trip_date': data['trip_date'],
        'purpose': data.get('purpose', 'Business'),
        'status': 'pending',
        'created_at': 'now()'
    }
    resp = supabase.table('mileage_claims').insert(claim_data).execute()
    if not resp.data:
        return jsonify({'error': 'Failed to submit claim'}), 500
    return jsonify(resp.data[0]), 201

@mileage_bp.route('/claims/user/<user_id>', methods=['GET'])
@require_auth
def get_user_claims(user, user_id):
    if user.id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    supabase = get_supabase()
    resp = supabase.table('mileage_claims')\
        .select('*')\
        .eq('user_id', user_id)\
        .order('trip_date', desc=True)\
        .execute()
    return jsonify(resp.data), 200
