# api/routes/mileage.py - FIXED (Remove JavaScript comments)
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import re

from services.supabase_client import get_supabase
from services.vin_validator import vin_validator
from services.mileage_rate import calculate_mileage_rate
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
        self.unit = data.get('unit', 'km')
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
    """Record a new mileage reading"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        required_fields = ['vin', 'odometer_reading']
        missing = [f for f in required_fields if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        vin = data['vin'].upper().strip()
        if not vin_validator.is_valid(vin):
            return jsonify({
                'success': False,
                'error': 'Invalid VIN format'
            }), 400
        
        odometer = data['odometer_reading']
        if not isinstance(odometer, (int, float)) or odometer < 0:
            return jsonify({
                'success': False,
                'error': 'Odometer reading must be a positive number'
            }), 400
        
        record = MileageRecord(data)
        supabase = get_supabase()
        
        previous = supabase.get_latest_mileage(vin)
        if previous:
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

@mileage_bp.route('/calculate-rate', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def calculate_rate():
    """Calculate mileage rate from vehicle data"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        result = calculate_mileage_rate(data)
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Calculate rate error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
