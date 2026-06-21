# api/routes/inspection.py – Inspection Routes
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import uuid

from services.inspection import (
    calculate_inspection,
    get_inspection_price,
    validate_inspection_data,
    quick_inspection
)
from services.supabase_client import get_supabase
from services.carapi_service import get_carapi_service
from services.vin_validator import vin_validator
from api.auth_middleware import require_auth
from utils.decorators import rate_limit, log_request

logger = logging.getLogger(__name__)

inspections_bp = Blueprint('inspections', __name__)

# ─── CREATE INSPECTION ──────────────────────────────────────────

@inspections_bp.route('/', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def create_inspection(user):
    """Create a new vehicle inspection."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    vehicle_data = data.get('vehicle_data', {})
    
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
            except Exception as e:
                logger.warning(f"CarAPI lookup failed: {str(e)}")

    # Validate required fields
    required = ['make', 'model', 'year']
    for field in required:
        if not vehicle_data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    # Validate data
    is_valid, error = validate_inspection_data(vehicle_data)
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

    # Get inspection parameters
    inspection_type = data.get('inspection_type', 'Premium')
    purpose = data.get('purpose', 'Pre-Purchase')
    region = data.get('region', 'Nairobi')

    # Calculate inspection
    try:
        result = calculate_inspection(
            make=vehicle_data.get('make'),
            model=vehicle_data.get('model'),
            year=int(vehicle_data.get('year', 0)),
            odometer=int(vehicle_data.get('odometer', 0)),
            engine_rating=vehicle_data.get('engine_rating', 'Good'),
            transmission_rating=vehicle_data.get('transmission_rating', 'Good'),
            suspension_rating=vehicle_data.get('suspension_rating', 'Good'),
            brakes_rating=vehicle_data.get('brakes_rating', 'Good'),
            paint_rating=vehicle_data.get('paint_rating', 'Good'),
            chassis_rating=vehicle_data.get('chassis_rating', 'Good'),
            interior_rating=vehicle_data.get('interior_rating', 'Good'),
            electronics_rating=vehicle_data.get('electronics_rating', 'Good'),
            tyre_depth_mm=float(vehicle_data.get('tyre_depth_mm', 6.0)),
            accident_history=vehicle_data.get('accident_history', 'none'),
            inspector_name=inspector.get('name'),
            inspector_credentials=inspector.get('credentials'),
            inspector_signature=inspector.get('signature'),
            inspection_type=inspection_type,
            region=region,
            purpose=purpose,
            inspector=inspector
        )
    except ValueError as e:
        return jsonify({'error': f'Invalid numeric value: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Inspection calculation error: {e}")
        return jsonify({'error': 'Inspection calculation failed'}), 500

    # Generate certificate number
    result['certificate_number'] = f"INS-{uuid.uuid4().hex[:8].upper()}"
    result['user_id'] = user.id

    # Save to Supabase
    supabase = get_supabase()
    request_data = {
        'user_id': user.id,
        'service_type': 'inspection',
        'registration_number': vehicle_data.get('registration_number'),
        'make': vehicle_data.get('make'),
        'model': vehicle_data.get('model'),
        'year': vehicle_data.get('year'),
        'odometer': vehicle_data.get('odometer'),
        'condition': vehicle_data.get('condition', 'Good'),
        'accident_history': vehicle_data.get('accident_history', 'None'),
        'inspection_type': inspection_type,
        'purpose': purpose,
        'amount': get_inspection_price(purpose),
        'payment_status': 'paid',
        'status': 'completed',
        'result': result,
        'inspector': inspector,
        'image_urls': data.get('image_urls', {}),
        'document_urls': data.get('document_urls', {}),
        'created_at': datetime.now().isoformat()
    }

    try:
        resp = supabase.table('service_requests').insert(request_data).execute()
        if not resp.data:
            logger.error("Failed to save inspection for user %s", user.id)
            return jsonify({'error': 'Failed to save inspection'}), 500
        return jsonify({
            'success': True,
            'data': resp.data[0],
            'inspection': result
        }), 201
    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500

# ─── GET INSPECTION ─────────────────────────────────────────────

@inspections_bp.route('/<inspection_id>', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_inspection(user, inspection_id):
    """Get inspection by ID."""
    supabase = get_supabase()
    try:
        resp = supabase.table('service_requests').select('*').eq('id', inspection_id).execute()
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
        return jsonify({'error': 'Failed to fetch inspection'}), 500

# ─── GET USER INSPECTIONS ──────────────────────────────────────

@inspections_bp.route('/user/<user_id>', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_user_inspections(user, user_id):
    """Get all inspections for a user."""
    if user.id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    supabase = get_supabase()
    try:
        resp = supabase.table('service_requests')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('service_type', 'inspection')\
            .order('created_at', desc=True)\
            .execute()
        return jsonify({
            'success': True,
            'data': resp.data,
            'count': len(resp.data)
        }), 200
    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Failed to fetch inspections'}), 500

# ─── QUICK INSPECTION ──────────────────────────────────────────

@inspections_bp.route('/quick-estimate', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def quick_estimate(user):
    """Quick inspection estimate."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    required = ['make', 'model', 'year']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    try:
        result = quick_inspection(
            make=data.get('make'),
            model=data.get('model'),
            year=int(data.get('year', 0)),
            odometer=int(data.get('odometer', 0)),
            condition=data.get('condition', 'good')
        )
        return jsonify({
            'success': True,
            'data': {
                'overall_score': result['overall_score'],
                'safety_score': result['safety_score'],
                'mechanical_score': result['mechanical_score'],
                'confidence_score': result['confidence_score'],
                'issues': result['issues'][:3]
            }
        }), 200
    except Exception as e:
        logger.error(f"Quick estimate error: {e}")
        return jsonify({'error': 'Calculation failed'}), 500

# ─── INSPECTION STATS ──────────────────────────────────────────

@inspections_bp.route('/stats', methods=['GET'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def get_inspection_stats(user):
    """Get inspection statistics."""
    supabase = get_supabase()
    try:
        resp = supabase.table('service_requests')\
            .select('*')\
            .eq('user_id', user.id)\
            .eq('service_type', 'inspection')\
            .execute()
        
        total = len(resp.data)
        completed = len([r for r in resp.data if r.get('status') == 'completed'])
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'completed': completed,
                'pending': total - completed,
                'avg_score': 0  # Would need to calculate from results
            }
        }), 200
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': 'Failed to fetch stats'}), 500
