# api/valuations.py – FIXED IMPORT
import uuid
import logging
from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from services.valuation_engine import calculate_value  # ✅ CORRECT
from api.auth_middleware import require_auth

logger = logging.getLogger(__name__)
valuations_bp = Blueprint('valuations', __name__)

@valuations_bp.route('/', methods=['POST'])
@require_auth
def create_valuation(user):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    vehicle_data = data.get('vehicle_data', {})
    purpose = data.get('purpose', 'market_value')

    # Validate required fields
    required = ['make', 'model', 'year']
    for field in required:
        if not vehicle_data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    # Call the function with correct parameters
    try:
        result = calculate_value(
            make=vehicle_data.get('make'),
            model=vehicle_data.get('model'),
            year=int(vehicle_data.get('year', 0)),
            odometer=int(vehicle_data.get('odometer', 0)),
            condition=vehicle_data.get('condition', 'good'),
            accident_history=vehicle_data.get('accident_history', 'none'),
            service_history=vehicle_data.get('service_history', 'full'),
            owners=int(vehicle_data.get('owners', 1)),
            usage=vehicle_data.get('usage', 'personal'),
            import_status=vehicle_data.get('import_status', 'local'),
            warranty=vehicle_data.get('warranty', 'expired'),
            modifications=vehicle_data.get('modifications', 'none'),
            region=vehicle_data.get('region', 'nairobi'),
            purpose=purpose
        )
    except ValueError as e:
        return jsonify({'error': f'Invalid numeric value: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Valuation calculation error: {e}")
        return jsonify({'error': 'Valuation calculation failed'}), 500

    # Generate certificate number
    result['certificate_number'] = f"VAL-{uuid.uuid4().hex[:8].upper()}"

    # Save to Supabase
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

    try:
        resp = supabase.table('service_requests').insert(request_data).execute()
        if not resp.data:
            logger.error("Failed to save valuation for user %s", user.id)
            return jsonify({'error': 'Failed to save valuation'}), 500
        return jsonify(resp.data[0]), 201
    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500


@valuations_bp.route('/user/<user_id>', methods=['GET'])
@require_auth
def get_user_valuations(user, user_id):
    if user.id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    supabase = get_supabase()
    try:
        resp = supabase.table('service_requests')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('service_type', 'valuation')\
            .order('created_at', desc=True)\
            .execute()
        return jsonify(resp.data), 200
    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Failed to fetch valuations'}), 500


@valuations_bp.route('/<valuation_id>', methods=['GET'])
@require_auth
def get_valuation(user, valuation_id):
    supabase = get_supabase()
    try:
        resp = supabase.table('service_requests').select('*').eq('id', valuation_id).execute()
        if not resp.data:
            return jsonify({'error': 'Not found'}), 404
        if resp.data[0]['user_id'] != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        return jsonify(resp.data[0]), 200
    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Failed to fetch valuation'}), 500
