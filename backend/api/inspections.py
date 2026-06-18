from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
import uuid

inspections_bp = Blueprint('inspections', __name__)

@inspections_bp.route('/', methods=['POST'])
def create_inspection():
    data = request.get_json()
    user_id = data.get('user_id')
    vehicle_data = data.get('vehicle_data', {})
    inspection_type = data.get('inspection_type', 'Standard')

    if not user_id or not vehicle_data:
        return jsonify({'error': 'user_id and vehicle_data required'}), 400

    # Mock scoring
    inspection_result = {
        'overall_score': 8.5,
        'exterior': 8.0,
        'interior': 7.5,
        'mechanical': 9.0,
        'electrical': 8.0,
        'safety': 8.5,
        'issues': ['Minor scratches on bumper'],
        'certificate_number': f"INS-{uuid.uuid4().hex[:8].upper()}"
    }

    supabase = get_supabase()
    request_data = {
        'user_id': user_id,
        'service_type': 'inspection',
        'registration_number': vehicle_data.get('registration_number'),
        'make': vehicle_data.get('make'),
        'model': vehicle_data.get('model'),
        'year': vehicle_data.get('year'),
        'odometer': vehicle_data.get('odometer'),
        'inspection_type': inspection_type,
        'amount': 3500,
        'payment_status': 'paid',
        'status': 'completed',
        'result': inspection_result,
        'created_at': 'now()'
    }
    resp = supabase.table('service_requests').insert(request_data).execute()
    if not resp.data:
        return jsonify({'error': 'Failed to save'}), 500
    return jsonify(resp.data[0]), 201

@inspections_bp.route('/user/<user_id>', methods=['GET'])
def get_user_inspections(user_id):
    supabase = get_supabase()
    resp = supabase.table('service_requests')\
        .select('*')\
        .eq('user_id', user_id)\
        .eq('service_type', 'inspection')\
        .order('created_at', desc=True)\
        .execute()
    return jsonify(resp.data), 200
