# api/routes/inspections.py - Inspection Routes
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import json

from services.supabase_client import get_supabase
from services.vin_validator import vin_validator
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

inspections_bp = Blueprint('inspections', __name__)

# ─── CREATE INSPECTION ─────────────────────────────────────────

@inspections_bp.route('/create', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def create_inspection():
    """Create a new vehicle inspection"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required = ['vin', 'inspector_name', 'inspection_date']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing fields: {", ".join(missing)}'
            }), 400
        
        # Validate VIN
        vin = data['vin'].upper().strip()
        if not vin_validator.is_valid(vin):
            return jsonify({'success': False, 'error': 'Invalid VIN format'}), 400
        
        # Prepare inspection data
        inspection_data = {
            'vin': vin,
            'inspector_name': data['inspector_name'],
            'inspector_license': data.get('inspector_license'),
            'inspection_date': data['inspection_date'],
            'location': data.get('location'),
            'vehicle_condition': data.get('vehicle_condition', 'Good'),
            'engine_score': data.get('engine_score', 8),
            'transmission_score': data.get('transmission_score', 8),
            'suspension_score': data.get('suspension_score', 8),
            'brake_score': data.get('brake_score', 8),
            'paint_score': data.get('paint_score', 8),
            'interior_score': data.get('interior_score', 8),
            'electronics_score': data.get('electronics_score', 8),
            'chassis_score': data.get('chassis_score', 8),
            'tyre_depth': data.get('tyre_depth'),
            'accident_history': data.get('accident_history', 'None'),
            'service_history': data.get('service_history', 'Full'),
            'notes': data.get('notes'),
            'image_urls': data.get('image_urls', []),
            'status': data.get('status', 'pending'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Save to Supabase
        supabase = get_supabase()
        result = supabase.save_inspection(inspection_data)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to save inspection')
            }), 500
        
        return jsonify({
            'success': True,
            'data': result.get('inspection'),
            'message': 'Inspection created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Create inspection error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── GET INSPECTION ────────────────────────────────────────────

@inspections_bp.route('/<inspection_id>', methods=['GET'])
@rate_limit(limit=50, per=60)
@require_auth
@log_request
def get_inspection(inspection_id):
    """Get inspection by ID"""
    try:
        supabase = get_supabase()
        result = supabase.get_inspection(inspection_id)
        
        if not result:
            return jsonify({'success': False, 'error': 'Inspection not found'}), 404
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
    except Exception as e:
        logger.error(f"Get inspection error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── GET INSPECTIONS BY VIN ────────────────────────────────────

@inspections_bp.route('/vehicle/<vin>', methods=['GET'])
@rate_limit(limit=50, per=60)
@require_auth
@log_request
def get_inspections_by_vin(vin):
    """Get all inspections for a vehicle"""
    try:
        vin = vin.upper().strip()
        
        supabase = get_supabase()
        results = supabase.get_inspections_by_vin(vin)
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        }), 200
    except Exception as e:
        logger.error(f"Get inspections by VIN error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── UPDATE INSPECTION ─────────────────────────────────────────

@inspections_bp.route('/<inspection_id>', methods=['PUT'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def update_inspection(inspection_id):
    """Update inspection"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        data['updated_at'] = datetime.now().isoformat()
        
        supabase = get_supabase()
        result = supabase.update_inspection(inspection_id, data)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to update inspection')
            }), 500
        
        return jsonify({
            'success': True,
            'data': result.get('inspection'),
            'message': 'Inspection updated successfully'
        }), 200
    except Exception as e:
        logger.error(f"Update inspection error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── UPDATE INSPECTION STATUS ─────────────────────────────────

@inspections_bp.route('/<inspection_id>/status', methods=['PUT'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def update_inspection_status(inspection_id):
    """Update inspection status"""
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': 'status is required'}), 400
        
        valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        status = data['status']
        
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        supabase = get_supabase()
        result = supabase.update_inspection_status(inspection_id, status)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to update status')
            }), 500
        
        return jsonify({
            'success': True,
            'data': {
                'inspection_id': inspection_id,
                'status': status,
                'updated_at': datetime.now().isoformat()
            },
            'message': f'Inspection status updated to {status}'
        }), 200
    except Exception as e:
        logger.error(f"Update inspection status error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── BATCH INSPECTIONS ─────────────────────────────────────────

@inspections_bp.route('/batch', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def batch_inspections():
    """Create multiple inspections in batch"""
    try:
        data = request.get_json()
        
        if not data or 'inspections' not in data:
            return jsonify({
                'success': False,
                'error': 'inspections array is required'
            }), 400
        
        inspections = data['inspections']
        
        if not isinstance(inspections, list):
            return jsonify({
                'success': False,
                'error': 'inspections must be an array'
            }), 400
        
        if len(inspections) > 50:
            return jsonify({
                'success': False,
                'error': 'Maximum 50 inspections per batch'
            }), 400
        
        results = []
        errors = []
        supabase = get_supabase()
        
        for idx, inspection_data in enumerate(inspections):
            try:
                inspection_data['created_at'] = datetime.now().isoformat()
                inspection_data['updated_at'] = datetime.now().isoformat()
                
                result = supabase.save_inspection(inspection_data)
                
                if result.get('success'):
                    results.append({
                        'index': idx,
                        'inspection_id': result.get('inspection', {}).get('id'),
                        'vin': inspection_data.get('vin'),
                        'success': True
                    })
                else:
                    errors.append({
                        'index': idx,
                        'error': result.get('error', 'Failed to save inspection')
                    })
            except Exception as e:
                errors.append({'index': idx, 'error': str(e)})
        
        return jsonify({
            'success': True,
            'data': {
                'created': len(results),
                'failed': len(errors),
                'results': results,
                'errors': errors
            },
            'message': f'Batch completed: {len(results)} created, {len(errors)} failed'
        }), 200
    except Exception as e:
        logger.error(f"Batch inspections error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── STATS ──────────────────────────────────────────────────────

@inspections_bp.route('/stats', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_inspection_stats():
    """Get inspection statistics"""
    try:
        supabase = get_supabase()
        stats = supabase.get_inspection_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Get inspection stats error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
