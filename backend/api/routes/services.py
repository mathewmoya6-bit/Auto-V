# api/routes/services.py - Service Routes
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from services.supabase_client import get_supabase
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

services_bp = Blueprint('services', __name__)

@services_bp.route('/', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_services():
    """Get all services"""
    try:
        services = [
            {'id': 'valuation', 'name': 'Vehicle Valuation', 'price': 2500},
            {'id': 'inspection', 'name': 'Vehicle Inspection', 'price': 3500},
            {'id': 'assessment', 'name': 'Vehicle Assessment', 'price': 3000},
            {'id': 'mileage', 'name': 'Mileage Rate Report', 'price': 1500},
            {'id': 'fleet', 'name': 'Fleet Services', 'price': 4000}
        ]
        
        return jsonify({
            'success': True,
            'data': services
        }), 200
    except Exception as e:
        logger.error(f"Get services error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@services_bp.route('/create', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def create_service_request():
    """Create a service request"""
    try:
        data = request.get_json()
        
        if not data or 'service_type' not in data:
            return jsonify({
                'success': False,
                'error': 'service_type is required'
            }), 400
        
        data['user_id'] = request.user_id
        data['created_at'] = datetime.now().isoformat()
        data['status'] = 'pending'
        
        supabase = get_supabase()
        response = supabase.table('service_requests').insert(data).execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'data': response.data[0],
                'message': 'Service request created'
            }), 201
        
        return jsonify({
            'success': False,
            'error': 'Failed to create service request'
        }), 500
    except Exception as e:
        logger.error(f"Create service error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
