# api/routes/assessments.py - Vehicle Damage Assessment Routes
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import json

from services.supabase_client import get_supabase
from services.vin_validation_service import comprehensive_fraud_check
from services.vin_validator import vin_validator
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

# Create blueprint
assessments_bp = Blueprint('assessments', __name__)

# ─── ASSESSMENT MODELS ─────────────────────────────────────────

class DamageAssessment:
    """Damage assessment model"""
    def __init__(self, data):
        self.vin = data.get('vin')
        self.user_id = data.get('user_id')
        self.vehicle_make = data.get('make')
        self.vehicle_model = data.get('model')
        self.vehicle_year = data.get('year')
        self.damage_type = data.get('damage_type')  # scratch, dent, crack, etc.
        self.severity = data.get('severity')  # minor, moderate, severe
        self.location = data.get('location')  # front, rear, side, etc.
        self.estimated_cost = data.get('estimated_cost')
        self.image_urls = data.get('image_urls', [])
        self.notes = data.get('notes')
        self.inspector_id = data.get('inspector_id')
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

# ─── ROUTES ──────────────────────────────────────────────────

@assessments_bp.route('/create', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def create_assessment():
    """
    Create a new damage assessment
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['vin', 'damage_type', 'severity', 'location']
        missing = [f for f in required_fields if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        # Validate VIN
        vin = data['vin'].upper().strip()
        if not vin_validator.is_valid(vin):
            return jsonify({
                'success': False,
                'error': 'Invalid VIN format'
            }), 400
        
        # Create assessment object
        assessment = DamageAssessment(data)
        
        # Save to Supabase
        supabase = get_supabase()
        result = supabase.save_assessment({
            'vin': assessment.vin,
            'user_id': assessment.user_id,
            'make': assessment.vehicle_make,
            'model': assessment.vehicle_model,
            'year': assessment.vehicle_year,
            'damage_type': assessment.damage_type,
            'severity': assessment.severity,
            'location': assessment.location,
            'estimated_cost': assessment.estimated_cost,
            'image_urls': assessment.image_urls,
            'notes': assessment.notes,
            'inspector_id': assessment.inspector_id,
            'created_at': assessment.created_at,
            'updated_at': assessment.updated_at,
            'status': 'pending'
        })
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to save assessment')
            }), 500
        
        return jsonify({
            'success': True,
            'data': {
                'assessment_id': result.get('data', {}).get('id'),
                'vin': assessment.vin,
                'damage_type': assessment.damage_type,
                'severity': assessment.severity,
                'estimated_cost': assessment.estimated_cost,
                'status': 'pending',
                'created_at': assessment.created_at
            },
            'message': 'Assessment created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Create assessment error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@assessments_bp.route('/<assessment_id>', methods=['GET'])
@rate_limit(limit=50, per=60)
@require_auth
@log_request
def get_assessment(assessment_id):
    """
    Get assessment by ID
    """
    try:
        supabase = get_supabase()
        result = supabase.get_assessment(assessment_id)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Assessment not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Get assessment error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@assessments_bp.route('/vehicle/<vin>', methods=['GET'])
@rate_limit(limit=50, per=60)
@require_auth
@log_request
def get_assessments_by_vin(vin):
    """
    Get all assessments for a vehicle
    """
    try:
        vin = vin.upper().strip()
        
        supabase = get_supabase()
        results = supabase.get_assessments_by_vin(vin)
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        }), 200
        
    except Exception as e:
        logger.error(f"Get assessments by VIN error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@assessments_bp.route('/<assessment_id>/status', methods=['PUT'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def update_assessment_status(assessment_id):
    """
    Update assessment status
    """
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400
        
        valid_statuses = ['pending', 'reviewed', 'approved', 'rejected', 'completed']
        status = data['status']
        
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        supabase = get_supabase()
        result = supabase.update_assessment_status(assessment_id, status)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to update status')
            }), 500
        
        return jsonify({
            'success': True,
            'data': {
                'assessment_id': assessment_id,
                'status': status,
                'updated_at': datetime.now().isoformat()
            },
            'message': f'Assessment status updated to {status}'
        }), 200
        
    except Exception as e:
        logger.error(f"Update assessment status error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@assessments_bp.route('/<assessment_id>/cost', methods=['PUT'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def update_assessment_cost(assessment_id):
    """
    Update estimated repair cost
    """
    try:
        data = request.get_json()
        
        if not data or 'estimated_cost' not in data:
            return jsonify({
                'success': False,
                'error': 'estimated_cost is required'
            }), 400
        
        estimated_cost = data['estimated_cost']
        
        if not isinstance(estimated_cost, (int, float)) or estimated_cost < 0:
            return jsonify({
                'success': False,
                'error': 'estimated_cost must be a positive number'
            }), 400
        
        supabase = get_supabase()
        result = supabase.update_assessment_cost(assessment_id, estimated_cost)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to update cost')
            }), 500
        
        return jsonify({
            'success': True,
            'data': {
                'assessment_id': assessment_id,
                'estimated_cost': estimated_cost,
                'updated_at': datetime.now().isoformat()
            },
            'message': 'Estimated cost updated successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Update assessment cost error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@assessments_bp.route('/batch', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def batch_assessments():
    """
    Create multiple assessments in batch
    """
    try:
        data = request.get_json()
        
        if not data or 'assessments' not in data:
            return jsonify({
                'success': False,
                'error': 'assessments array is required'
            }), 400
        
        assessments = data['assessments']
        
        if not isinstance(assessments, list):
            return jsonify({
                'success': False,
                'error': 'assessments must be an array'
            }), 400
        
        if len(assessments) > 50:
            return jsonify({
                'success': False,
                'error': 'Maximum 50 assessments per batch'
            }), 400
        
        results = []
        errors = []
        
        supabase = get_supabase()
        
        for idx, assessment_data in enumerate(assessments):
            try:
                # Validate required fields
                required_fields = ['vin', 'damage_type', 'severity', 'location']
                missing = [f for f in required_fields if not assessment_data.get(f)]
                
                if missing:
                    errors.append({
                        'index': idx,
                        'error': f'Missing fields: {", ".join(missing)}'
                    })
                    continue
                
                # Validate VIN
                vin = assessment_data['vin'].upper().strip()
                if not vin_validator.is_valid(vin):
                    errors.append({
                        'index': idx,
                        'error': 'Invalid VIN format'
                    })
                    continue
                
                # Create assessment
                assessment = DamageAssessment(assessment_data)
                result = supabase.save_assessment({
                    'vin': assessment.vin,
                    'user_id': assessment.user_id,
                    'make': assessment.vehicle_make,
                    'model': assessment.vehicle_model,
                    'year': assessment.vehicle_year,
                    'damage_type': assessment.damage_type,
                    'severity': assessment.severity,
                    'location': assessment.location,
                    'estimated_cost': assessment.estimated_cost,
                    'image_urls': assessment.image_urls,
                    'notes': assessment.notes,
                    'inspector_id': assessment.inspector_id,
                    'created_at': assessment.created_at,
                    'updated_at': assessment.updated_at,
                    'status': 'pending'
                })
                
                if result.get('success'):
                    results.append({
                        'index': idx,
                        'assessment_id': result.get('data', {}).get('id'),
                        'vin': assessment.vin,
                        'success': True
                    })
                else:
                    errors.append({
                        'index': idx,
                        'error': result.get('error', 'Failed to save assessment')
                    })
                    
            except Exception as e:
                errors.append({
                    'index': idx,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'data': {
                'created': len(results),
                'failed': len(errors),
                'results': results,
                'errors': errors
            },
            'message': f'Batch assessment completed: {len(results)} created, {len(errors)} failed'
        }), 200
        
    except Exception as e:
        logger.error(f"Batch assessment error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@assessments_bp.route('/stats', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_assessment_stats():
    """
    Get assessment statistics
    """
    try:
        supabase = get_supabase()
        stats = supabase.get_assessment_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Get assessment stats error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
