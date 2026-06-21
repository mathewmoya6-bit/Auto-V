# api/routes/assessments.py - Assessment Routes
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import uuid

from services.supabase_client import get_supabase
from services.assessment import run_assessment
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

# ─── CREATE BLUEPRINT ──────────────────────────────────────────

assessments_bp = Blueprint('assessments', __name__)

@assessments_bp.route('/create', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def create_assessment():
    """Create a vehicle assessment"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        assessment_type = data.get('assessment_type')
        if not assessment_type:
            return jsonify({
                'success': False,
                'error': 'assessment_type is required'
            }), 400
        
        # Get vehicle data
        vehicle = data.get('vehicle', {})
        if not vehicle.get('make') or not vehicle.get('model'):
            return jsonify({
                'success': False,
                'error': 'Vehicle make and model are required'
            }), 400
        
        # Add user_id
        data['user_id'] = request.user_id
        
        # Run assessment
        result = run_assessment(assessment_type, **data)
        
        # Save to Supabase
        supabase = get_supabase()
        save_data = {
            'user_id': request.user_id,
            'assessment_type': assessment_type,
            'vehicle_data': vehicle,
            'result': result,
            'created_at': datetime.now().isoformat()
        }
        
        response = supabase.table('assessments').insert(save_data).execute()
        
        if response.data:
            result['id'] = response.data[0].get('id')
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Assessment completed successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Create assessment error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
