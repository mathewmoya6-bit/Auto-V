import uuid
import logging
from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from services.valuation_engine import calculate_valuation
from api.auth_middleware import require_auth

logger = logging.getLogger(__name__)
valuations_bp = Blueprint('valuations', __name__)

@valuations_bp.route('/', methods=['POST'])
@require_auth
def create_valuation(user):
    data = request.get_json()
    vehicle_data = data.get('vehicle_data', {})
    purpose = data.get('purpose', 'Market Value')

    # Validate required fields
    required = ['make', 'model', 'year']
    for field in required:
        if not vehicle_data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    result = calculate_valuation(vehicle_data)
    result['certificate_number'] = f"VAL-{uuid.uuid4().hex[:8].upper()}"

    supabase = get_supabase()
    request_data = {
        'user_id': user.id,
        'service_type': 'valuation',
        'registration_number': vehicle_data.get('registration_number'),
        'make': vehicle_data.get('make'),
        'model': vehicle_data.get('model'),
        'year': vehicle_data.get('year'),
        'odometer': vehicle_data.get('odometer'),
        'condition': vehicle_data.get('condition', 'Good'),
        'accident_history': vehicle_data.get('accident_history', 'None'),
        'valuation_purpose': purpose,
        'amount': 2500,
        'payment_status': 'paid',
        'status': 'completed',
        'result': result,
        'created_at': 'now()'
    }
    resp = supabase.table('service_requests').insert(request_data).execute()
    if not resp.data:
        logger.error("Failed to save valuation for user %s", user.id)
        return jsonify({'error': 'Failed to save valuation'}), 500
    return jsonify(resp.data[0]), 201

@valuations_bp.route('/user/<user_id>', methods=['GET'])
@require_auth
def get_user_valuations(user, user_id):
    # Ensure user can only access their own data
    if user.id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    supabase = get_supabase()
    resp = supabase.table('service_requests')\
        .select('*')\
        .eq('user_id', user_id)\
        .eq('service_type', 'valuation')\
        .order('created_at', desc=True)\
        .execute()
    return jsonify(resp.data), 200

@valuations_bp.route('/<valuation_id>', methods=['GET'])
@require_auth
def get_valuation(user, valuation_id):
    supabase = get_supabase()
    resp = supabase.table('service_requests').select('*').eq('id', valuation_id).execute()
    if not resp.data:
        return jsonify({'error': 'Not found'}), 404
    # Check ownership
    if resp.data[0]['user_id'] != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify(resp.data[0]), 200
