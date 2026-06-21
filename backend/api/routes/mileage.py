# api/routes/mileage.py - Mileage & Odometer Routes
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import re

from services.supabase_client import get_supabase
from services.vin_validator import vin_validator
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

# Create blueprint
mileage_bp = Blueprint('mileage', __name__)

# ─── MILEAGE MODELS ────────────────────────────────────────────

class MileageRecord:
    """Mileage record model"""
    def __init__(self, data):
        self.vin = data.get('vin')
        self.user_id = data.get('user_id')
        self.odometer_reading = data.get('odometer_reading')
        self.unit = data.get('unit', 'km')  # km or miles
        self.reading_date = data.get('reading_date', datetime.now().isoformat())
        self.reading_location = data.get('reading_location')
        self.notes = data.get('notes')
        self.image_url = data.get('image_url')
        self.verified_by = data.get('verified_by')
        self.verification_status = data.get('verification_status', 'pending')
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

# ─── ROUTES ──────────────────────────────────────────────────

@mileage_bp.route('/record', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def record_mileage():
    """
    Record a new mileage reading
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['vin', 'odometer_reading']
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
        
        # Validate odometer reading
        odometer = data['odometer_reading']
        if not isinstance(odometer, (int, float)) or odometer < 0:
            return jsonify({
                'success': False,
                'error': 'Odometer reading must be a positive number'
            }), 400
        
        # Create mileage record
        record = MileageRecord(data)
        
        # Save to Supabase
        supabase = get_supabase()
        
        # Check for previous reading
        previous = supabase.get_latest_mileage(vin)
        if previous:
            # Calculate mileage difference
            diff = odometer - previous.get('odometer_reading', 0)
            if diff < 0:
                return jsonify({
                    'success': False,
                    'error': f'Odometer reading ({odometer}) is less than previous reading ({previous.get("odometer_reading")})'
                }), 400
        
        result = supabase.save_mileage_record({
            'vin': record.vin,
            'user_id': record.user_id,
            'odometer_reading': record.odometer_reading,
            'unit': record.unit,
            'reading_date': record.reading_date,
            'reading_location': record.reading_location,
            'notes': record.notes,
            'image_url': record.image_url,
            'verified_by': record.verified_by,
            'verification_status': record.verification_status,
            'created_at': record.created_at,
            'updated_at': record.updated_at
        })
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to save mileage record')
            }), 500
        
        return jsonify({
            'success': True,
            'data': {
                'record_id': result.get('data', {}).get('id'),
                'vin': record.vin,
                'odometer_reading': record.odometer_reading,
                'unit': record.unit,
                'reading_date': record.reading_date,
                'verified_by': record.verified_by,
                'verification_status': record.verification_status
            },
            'message': 'Mileage recorded successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Record mileage error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/<record_id>', methods=['GET'])
@rate_limit(limit=50, per=60)
@require_auth
@log_request
def get_mileage_record(record_id):
    """
    Get mileage record by ID
    """
    try:
        supabase = get_supabase()
        result = supabase.get_mileage_record(record_id)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Mileage record not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Get mileage record error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/vehicle/<vin>', methods=['GET'])
@rate_limit(limit=50, per=60)
@require_auth
@log_request
def get_mileage_history(vin):
    """
    Get mileage history for a vehicle
    """
    try:
        vin = vin.upper().strip()
        
        supabase = get_supabase()
        results = supabase.get_mileage_history(vin)
        
        # Calculate statistics
        stats = {}
        if results:
            readings = [r.get('odometer_reading', 0) for r in results]
            stats = {
                'first_reading': results[-1].get('odometer_reading') if results else None,
                'latest_reading': results[0].get('odometer_reading') if results else None,
                'total_readings': len(results),
                'average_mileage': sum(readings) / len(readings) if readings else 0,
                'highest_reading': max(readings) if readings else 0,
                'lowest_reading': min(readings) if readings else 0
            }
        
        return jsonify({
            'success': True,
            'data': results,
            'stats': stats,
            'count': len(results)
        }), 200
        
    except Exception as e:
        logger.error(f"Get mileage history error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/<record_id>/verify', methods=['PUT'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def verify_mileage(record_id):
    """
    Verify a mileage record
    """
    try:
        data = request.get_json()
        
        if not data or 'verified_by' not in data:
            return jsonify({
                'success': False,
                'error': 'verified_by is required'
            }), 400
        
        supabase = get_supabase()
        result = supabase.verify_mileage_record(
            record_id,
            data['verified_by'],
            data.get('notes', '')
        )
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to verify mileage record')
            }), 500
        
        return jsonify({
            'success': True,
            'data': {
                'record_id': record_id,
                'verified_by': data['verified_by'],
                'verification_status': 'verified',
                'verified_at': datetime.now().isoformat()
            },
            'message': 'Mileage record verified successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Verify mileage error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/<record_id>', methods=['DELETE'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def delete_mileage_record(record_id):
    """
    Delete a mileage record
    """
    try:
        supabase = get_supabase()
        result = supabase.delete_mileage_record(record_id)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to delete mileage record')
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Mileage record deleted successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Delete mileage record error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/check-mileage/<vin>', methods=['GET'])
@rate_limit(limit=30, per=60)
@log_request
def check_mileage_consistency(vin):
    """
    Check mileage consistency for a vehicle
    """
    try:
        vin = vin.upper().strip()
        
        if not vin_validator.is_valid(vin):
            return jsonify({
                'success': False,
                'error': 'Invalid VIN format'
            }), 400
        
        supabase = get_supabase()
        results = supabase.get_mileage_history(vin)
        
        if len(results) < 2:
            return jsonify({
                'success': True,
                'data': {
                    'vin': vin,
                    'has_enough_data': False,
                    'message': 'Not enough mileage records for consistency check'
                }
            }), 200
        
        # Check for inconsistencies
        inconsistencies = []
        warnings = []
        
        # Sort by reading date
        results.sort(key=lambda x: x.get('reading_date', ''))
        
        for i in range(1, len(results)):
            current = results[i]
            previous = results[i-1]
            
            current_reading = current.get('odometer_reading', 0)
            previous_reading = previous.get('odometer_reading', 0)
            
            diff = current_reading - previous_reading
            
            # Check for negative difference (rolled back)
            if diff < 0:
                inconsistencies.append({
                    'date': current.get('reading_date'),
                    'reading': current_reading,
                    'previous_reading': previous_reading,
                    'difference': diff,
                    'issue': 'Odometer rolled back'
                })
            
            # Check for unrealistic yearly mileage
            # Calculate days between readings
            try:
                current_date = datetime.fromisoformat(current.get('reading_date', ''))
                previous_date = datetime.fromisoformat(previous.get('reading_date', ''))
                days = (current_date - previous_date).days
                
                if days > 0:
                    daily_mileage = diff / days
                    yearly_mileage = daily_mileage * 365
                    
                    # Unrealistic yearly mileage (> 100,000 km/year)
                    if yearly_mileage > 100000:
                        warnings.append({
                            'date': current.get('reading_date'),
                            'reading': current_reading,
                            'yearly_mileage': round(yearly_mileage),
                            'issue': 'Unrealistically high mileage'
                        })
            except:
                pass
        
        # Determine overall status
        status = 'consistent'
        if inconsistencies:
            status = 'inconsistent'
        elif warnings:
            status = 'warning'
        
        return jsonify({
            'success': True,
            'data': {
                'vin': vin,
                'status': status,
                'has_enough_data': True,
                'total_readings': len(results),
                'latest_reading': results[-1].get('odometer_reading'),
                'earliest_reading': results[0].get('odometer_reading'),
                'inconsistencies': inconsistencies,
                'warnings': warnings,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Check mileage consistency error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/stats', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_mileage_stats():
    """
    Get mileage statistics
    """
    try:
        supabase = get_supabase()
        stats = supabase.get_mileage_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Get mileage stats error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
