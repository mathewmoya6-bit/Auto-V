# api/routes/vin_routes.py
from flask import Blueprint, request, jsonify
from services.vin_ocr import extract_vin_from_image
from services.vin_validation_service import validate_vin_against_db, comprehensive_fraud_check
from services.vin_validator import vin_validator
from services.carapi_service import car_api
from services.supabase_client import get_supabase
from utils.decorators import rate_limit, require_auth, log_request
import logging

logger = logging.getLogger(__name__)

# Create blueprint
router = Blueprint('vin', __name__)

@router.route('/scan', methods=['POST'])
@rate_limit(limit=10, per=60)
@log_request
def scan_vin():
    """Scan VIN from image URL"""
    try:
        data = request.get_json()
        
        if not data or 'image_url' not in data:
            return jsonify({
                'success': False,
                'error': 'image_url is required'
            }), 400
        
        image_url = data['image_url']
        user_id = data.get('user_id')
        ip_address = data.get('ip_address')
        
        # Extract VIN from image
        ocr_result = extract_vin_from_image(image_url)
        
        if not ocr_result.get('extracted'):
            return jsonify({
                'success': False,
                'error': 'Failed to extract VIN from image',
                'validation': {
                    'match': False,
                    'risk': 'HIGH',
                    'reason': 'OCR extraction failed'
                }
            }), 400
        
        vin = ocr_result.get('vin')
        
        if not vin:
            return jsonify({
                'success': False,
                'error': 'No VIN detected in image',
                'validation': {
                    'match': False,
                    'risk': 'HIGH',
                    'reason': 'No VIN found'
                }
            }), 400
        
        # Validate VIN format
        validation_result = vin_validator.validate(vin)
        
        if not validation_result.get('valid'):
            return jsonify({
                'success': False,
                'vin': vin,
                'error': 'Invalid VIN format',
                'validation': {
                    'match': False,
                    'risk': 'HIGH',
                    'reason': 'Invalid VIN format',
                    'errors': validation_result.get('errors', []),
                    'suggestions': vin_validator.suggest_corrections(vin)
                }
            }), 400
        
        # Check against database
        db_validation = validate_vin_against_db(vin)
        
        # Fraud detection
        fraud_check = comprehensive_fraud_check(
            vin=vin,
            user_id=user_id,
            ip_address=ip_address
        )
        
        # Get vehicle details if valid
        vehicle = None
        if db_validation.get('match'):
            vehicle = db_validation.get('vehicle')
            
            # If vehicle found but no details, fetch from CarAPI
            if vehicle and not vehicle.get('make'):
                car_data = car_api.decode_vin(vin)
                if 'error' not in car_data:
                    vehicle.update(car_data)
        
        # Save scan record
        try:
            supabase = get_supabase()
            if user_id:
                supabase.save_vin_scan(
                    user_id=user_id,
                    vin=vin,
                    image_url=image_url,
                    status='verified' if db_validation.get('match') else 'pending'
                )
        except Exception as e:
            logger.warning(f"Failed to save scan record: {str(e)}")
        
        return jsonify({
            'success': True,
            'vin': vin,
            'validation': db_validation,
            'fraud_check': fraud_check,
            'vehicle': vehicle,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"VIN scan error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
