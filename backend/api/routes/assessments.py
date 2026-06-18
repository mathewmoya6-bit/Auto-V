# api/routes/assessments.py - Assessment Flask Routes

import logging
import sys
import os
from datetime import datetime
from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from api.auth_middleware import require_auth

# ─── Fix Import Path ──────────────────────────────────────────
# Get the absolute path to the backend directory
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add it to Python path if not already there
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Now try to import from assessment engine
try:
    from assessment import assess, ASSESSMENT_TYPES
    logger = logging.getLogger(__name__)
    logger.info("✅ Successfully imported assessment engine")
except ImportError as e:
    # If import fails, use fallback
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import assessment: {e}")
    # Create fallback functions if assessment.py is missing
    ASSESSMENT_TYPES = ["accident", "insurance_claim", "repair_cost", "total_loss", "salvage", "theft_recovery"]
    def assess(assessment_type, **kwargs):
        return {
            "error": "Assessment engine not available",
            "assessment_type": assessment_type,
            "message": "Please ensure assessment.py is in the backend directory"
        }

logger = logging.getLogger(__name__)

# ─── Blueprint ────────────────────────────────────────────────
assessments_bp = Blueprint('assessments', __name__)


@assessments_bp.route('/', methods=['GET'])
@require_auth
def get_assessments(user):
    """Get all assessments for the current user."""
    try:
        supabase = get_supabase()
        response = supabase.table('assessments')\
            .select('*')\
            .eq('user_id', user.id)\
            .order('created_at', desc=True)\
            .execute()
        return jsonify(response.data), 200
    except Exception as e:
        logger.error(f"Error fetching assessments: {e}")
        return jsonify({'error': 'Failed to fetch assessments'}), 500


@assessments_bp.route('/<assessment_id>', methods=['GET'])
@require_auth
def get_assessment(user, assessment_id):
    """Get a specific assessment by ID."""
    try:
        supabase = get_supabase()
        response = supabase.table('assessments')\
            .select('*')\
            .eq('id', assessment_id)\
            .eq('user_id', user.id)\
            .execute()
        
        if not response.data:
            return jsonify({'error': 'Assessment not found'}), 404
        
        return jsonify(response.data[0]), 200
    except Exception as e:
        logger.error(f"Error fetching assessment: {e}")
        return jsonify({'error': 'Failed to fetch assessment'}), 500


@assessments_bp.route('/types', methods=['GET'])
@require_auth
def get_assessment_types(user):
    """Get all available assessment types."""
    return jsonify({
        'types': ASSESSMENT_TYPES,
        'description': 'Available assessment types for the AUTO-V AI engine'
    }), 200


@assessments_bp.route('/run', methods=['POST'])
@require_auth
def run_assessment(user):
    """
    Run an assessment using the AUTO-V AI engine.
    
    Expected payload:
    {
        "assessment_type": "accident|insurance_claim|repair_cost|total_loss|salvage|theft_recovery",
        ... assessment-specific parameters
    }
    """
    try:
        data = request.get_json()
        
        # Validate assessment type
        assessment_type = data.get('assessment_type')
        if not assessment_type:
            return jsonify({'error': 'assessment_type is required'}), 400
        
        if assessment_type not in ASSESSMENT_TYPES:
            return jsonify({
                'error': f'Invalid assessment_type. Must be one of: {", ".join(ASSESSMENT_TYPES)}'
            }), 400
        
        # Remove assessment_type from kwargs
        kwargs = {k: v for k, v in data.items() if k != 'assessment_type'}
        
        # Run the assessment
        result = assess(assessment_type, **kwargs)
        
        # Store assessment in Supabase
        supabase = get_supabase()
        storage_data = {
            'user_id': user.id,
            'assessment_type': assessment_type,
            'result': result,
            'input_data': data,
            'created_at': datetime.now().isoformat()
        }
        
        response = supabase.table('assessments').insert(storage_data).execute()
        
        if response.data:
            result['saved'] = True
            result['assessment_id'] = response.data[0]['id']
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Assessment error: {e}")
        return jsonify({'error': str(e)}), 500


@assessments_bp.route('/', methods=['POST'])
@require_auth
def create_assessment(user):
    """Create a new assessment record (legacy endpoint)."""
    try:
        data = request.get_json()
        data['user_id'] = user.id
        data['created_at'] = datetime.now().isoformat()
        
        supabase = get_supabase()
        response = supabase.table('assessments').insert(data).execute()
        
        if not response.data:
            return jsonify({'error': 'Failed to create assessment'}), 500
        
        return jsonify(response.data[0]), 201
    except Exception as e:
        logger.error(f"Error creating assessment: {e}")
        return jsonify({'error': 'Failed to create assessment'}), 500


@assessments_bp.route('/<assessment_id>', methods=['PUT'])
@require_auth
def update_assessment(user, assessment_id):
    """Update an assessment."""
    try:
        data = request.get_json()
        data['updated_at'] = datetime.now().isoformat()
        
        supabase = get_supabase()
        response = supabase.table('assessments')\
            .update(data)\
            .eq('id', assessment_id)\
            .eq('user_id', user.id)\
            .execute()
        
        if not response.data:
            return jsonify({'error': 'Assessment not found or not authorized'}), 404
        
        return jsonify(response.data[0]), 200
    except Exception as e:
        logger.error(f"Error updating assessment: {e}")
        return jsonify({'error': 'Failed to update assessment'}), 500


@assessments_bp.route('/<assessment_id>', methods=['DELETE'])
@require_auth
def delete_assessment(user, assessment_id):
    """Delete an assessment."""
    try:
        supabase = get_supabase()
        response = supabase.table('assessments')\
            .delete()\
            .eq('id', assessment_id)\
            .eq('user_id', user.id)\
            .execute()
        
        if not response.data:
            return jsonify({'error': 'Assessment not found or not authorized'}), 404
        
        return jsonify({'message': 'Assessment deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting assessment: {e}")
        return jsonify({'error': 'Failed to delete assessment'}), 500
