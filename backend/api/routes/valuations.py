# api/routes/valuations.py – Fixed Import and Production Ready
import uuid
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime

from services.supabase_client import get_supabase
from services.valuation import calculate_value, get_valuation_price, validate_valuation_data
from services.carapi_service import get_carapi_service
from services.vin_validator import vin_validator
from api.auth_middleware import require_auth
from utils.decorators import rate_limit, log_request

logger = logging.getLogger(__name__)

valuations_bp = Blueprint('valuations', __name__)

# ─── CREATE VALUATION ────────────────────────────────────────────

@valuations_bp.route('/', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def create_valuation(user):
    """Create a new vehicle valuation"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    vehicle_data = data.get('vehicle_data', {})
    purpose = data.get('purpose', 'market_value')
    
    # If VIN provided, try to auto-fill
    vin = vehicle_data.get('vin')
    if vin:
        vin = vin.upper().strip()
        if vin_validator.is_valid(vin):
            try:
                carapi = get_carapi_service()
                vin_data = carapi.decode_vin(vin)
                if 'error' not in vin_data:
                    vehicle_data['make'] = vin_data.get('make', vehicle_data.get('make'))
                    vehicle_data['model'] = vin_data.get('model', vehicle_data.get('model'))
                    vehicle_data['year'] = vin_data.get('year', vehicle_data.get('year'))
                    vehicle_data['engine_cc'] = vin_data.get('engine_cc')
            except Exception as e:
                logger.warning(f"CarAPI lookup failed: {str(e)}")

    # Validate required fields
    required = ['make', 'model', 'year']
    for field in required:
        if not vehicle_data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    # Validate data
    is_valid, error = validate_valuation_data(vehicle_data)
    if not is_valid:
        return jsonify({'error': error}), 400

    # Get inspector from data or use default
    inspector = data.get('inspector', {})
    if not inspector.get('name'):
        inspector = {
            'name': user.user_metadata.get('full_name') if hasattr(user, 'user_metadata') else user.email,
            'credentials': 'AUTO-V-System',
            'signature': user.email
        }

    # Call valuation engine
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
            purpose=purpose,
            valuation_methodology=vehicle_data.get('methodology', 'market_comparison'),
            inspector=inspector,
            current_year=datetime.now().year
        )
    except ValueError as e:
        return jsonify({'error': f'Invalid numeric value: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Valuation calculation error: {e}")
        return jsonify({'error': 'Valuation calculation failed'}), 500

    # Generate certificate number
    result['certificate_number'] = f"VAL-{uuid.uuid4().hex[:8].upper()}"
    result['user_id'] = user.id

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
        'amount': get_valuation_price(purpose),
        'payment_status': 'paid',
        'status': 'completed',
        'result': result,
        'inspector': inspector,
        'created_at': datetime.now().isoformat()
    }

    try:
        resp = supabase.table('service_requests').insert(request_data).execute()
        if not resp.data:
            logger.error("Failed to save valuation for user %s", user.id)
            return jsonify({'error': 'Failed to save valuation'}), 500
        return jsonify({
            'success': True,
            'data': resp.data[0],
            'valuation': result
        }), 201
    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500

# ─── GET VALUATION ───────────────────────────────────────────────

@valuations_bp.route('/<valuation_id>', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_valuation(user, valuation_id):
    """Get valuation by ID"""
    supabase = get_supabase()
    try:
        resp = supabase.table('service_requests').select('*').eq('id', valuation_id).execute()
        if not resp.data:
            return jsonify({'error': 'Not found'}), 404
        if resp.data[0]['user_id'] != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        return jsonify({
            'success': True,
            'data': resp.data[0]
        }), 200
    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Failed to fetch valuation'}), 500

# ─── GET USER VALUATIONS ─────────────────────────────────────────

@valuations_bp.route('/user/<user_id>', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_user_valuations(user, user_id):
    """Get all valuations for a user"""
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
        return jsonify({
            'success': True,
            'data': resp.data,
            'count': len(resp.data)
        }), 200
    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Failed to fetch valuations'}), 500

# ─── GET VALUATIONS BY VIN ──────────────────────────────────────

@valuations_bp.route('/vehicle/<vin>', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_valuations_by_vin(user, vin):
    """Get all valuations for a vehicle"""
    vin = vin.upper().strip()
    
    supabase = get_supabase()
    try:
        resp = supabase.table('service_requests')\
            .select('*')\
            .eq('vin', vin)\
            .eq('service_type', 'valuation')\
            .order('created_at', desc=True)\
            .execute()
        return jsonify({
            'success': True,
            'data': resp.data,
            'count': len(resp.data)
        }), 200
    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Failed to fetch valuations'}), 500

# ─── QUICK ESTIMATE ─────────────────────────────────────────────

@valuations_bp.route('/quick-estimate', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def quick_estimate(user):
    """Quick valuation estimate (for instant check)"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    required = ['make', 'model', 'year']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    try:
        result = calculate_value(
            make=data.get('make'),
            model=data.get('model'),
            year=int(data.get('year', 0)),
            odometer=int(data.get('odometer', 0)),
            condition=data.get('condition', 'good'),
            accident_history='none',
            service_history='full',
            owners=1,
            usage='personal',
            import_status='local',
            warranty='expired',
            modifications='none',
            region='nairobi',
            purpose='market_value'
        )
        return jsonify({
            'success': True,
            'data': {
                'market_value': result['market_value'],
                'insurance_value': result['insurance_value'],
                'forced_sale_value': result['forced_sale_value'],
                'confidence_score': result['confidence_score']
            }
        }), 200
    except Exception as e:
        logger.error(f"Quick estimate error: {e}")
        return jsonify({'error': 'Calculation failed'}), 500

# ─── VALUATION STATS ────────────────────────────────────────────

@valuations_bp.route('/stats', methods=['GET'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def get_valuation_stats(user):
    """Get valuation statistics"""
    supabase = get_supabase()
    try:
        resp = supabase.table('service_requests')\
            .select('*')\
            .eq('user_id', user.id)\
            .eq('service_type', 'valuation')\
            .execute()
        
        total = len(resp.data)
        completed = len([r for r in resp.data if r.get('status') == 'completed'])
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'completed': completed,
                'pending': total - completed
            }
        }), 200
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': 'Failed to fetch stats'}), 500
