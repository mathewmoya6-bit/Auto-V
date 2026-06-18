from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from services.mileage_engine import calculate_mileage_rate

mileage_bp = Blueprint('mileage', __name__)

@mileage_bp.route('/calculate', methods=['POST'])
def calculate():
    """
    Calculate mileage reimbursement rate.
    Expects: vehicle_data, annual_km, fuel_type, etc.
    """
    data = request.get_json()
    
    # Required fields
    required = ['make', 'model', 'year', 'fuel_type', 'annual_km', 'purchase_price']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Additional optional fields with defaults
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
        'fuel_economy': data.get('fuel_economy'),  # Optional
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

    # Calculate rate
    result = calculate_mileage_rate(vehicle_data)
    
    # Save to database (optional)
    # user_id = data.get('user_id')
    # if user_id:
    #     supabase = get_supabase()
    #     supabase.table('mileage_calculations').insert({
    #         'user_id': user_id,
    #         'vehicle_data': vehicle_data,
    #         'result': result,
    #         'created_at': 'now()'
    #     }).execute()

    return jsonify(result), 200

@mileage_bp.route('/rates', methods=['GET'])
def get_rates():
    """Get all active mileage rates by vehicle category."""
    supabase = get_supabase()
    resp = supabase.table('mileage_rates')\
        .select('*')\
        .eq('is_active', True)\
        .order('rate_per_km')\
        .execute()
    return jsonify(resp.data), 200

@mileage_bp.route('/rates', methods=['POST'])
def add_rate():
    """Add a new mileage rate (admin only)."""
    data = request.get_json()
    required = ['vehicle_category', 'rate_per_km', 'effective_from']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    supabase = get_supabase()
    resp = supabase.table('mileage_rates').insert({
        'vehicle_category': data['vehicle_category'],
        'rate_per_km': float(data['rate_per_km']),
        'effective_from': data['effective_from'],
        'effective_to': data.get('effective_to'),
        'is_active': data.get('is_active', True)
    }).execute()
    
    if not resp.data:
        return jsonify({'error': 'Failed to add rate'}), 500
    return jsonify(resp.data[0]), 201

@mileage_bp.route('/claims', methods=['POST'])
def submit_claim():
    """Submit a mileage claim."""
    data = request.get_json()
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    required = ['trip_date', 'start_location', 'end_location', 'distance_km', 'vehicle_category']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
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
        'user_id': user_id,
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
def get_user_claims(user_id):
    supabase = get_supabase()
    resp = supabase.table('mileage_claims')\
        .select('*')\
        .eq('user_id', user_id)\
        .order('trip_date', desc=True)\
        .execute()
    return jsonify(resp.data), 200

@mileage_bp.route('/claims/<claim_id>', methods=['PUT'])
def update_claim_status(claim_id):
    """Update claim status (approve/reject)."""
    data = request.get_json()
    status = data.get('status')
    if status not in ['approved', 'rejected']:
        return jsonify({'error': 'Invalid status'}), 400
    
    supabase = get_supabase()
    resp = supabase.table('mileage_claims')\
        .update({'status': status, 'updated_at': 'now()'})\
        .eq('id', claim_id)\
        .execute()
    if not resp.data:
        return jsonify({'error': 'Claim not found'}), 404
    return jsonify(resp.data[0]), 200
