# backend/api/vin_routes.py
from flask import Blueprint, request, jsonify
from services.vin_validator import vin_validator
from services.carapi_service import car_api
from services.vin_ocr import vin_ocr
from utils.decorators import rate_limit, require_auth
import logging

bp = Blueprint('vin', __name__, url_prefix='/api/vin')
logger = logging.getLogger(__name__)

@bp.route('/validate', methods=['POST'])
@rate_limit(limit=100, per=60)
def validate_vin():
    """
    Validate a VIN number
    
    Request body:
    {
        "vin": "JTEGD34V000123456"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'vin' not in data:
            return jsonify({
                'success': False,
                'error': 'vin is required'
            }), 400
        
        vin = data['vin']
        result = vin_validator.validate(vin)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"VIN validation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/batch-validate', methods=['POST'])
@rate_limit(limit=50, per=60)
def batch_validate_vin():
    """
    Validate multiple VIN numbers
    
    Request body:
    {
        "vins": ["JTEGD34V000123456", "JTEGD34V000123457"]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'vins' not in data:
            return jsonify({
                'success': False,
                'error': 'vins is required'
            }), 400
        
        results = []
        for vin in data['vins']:
            result = vin_validator.validate(vin)
            results.append(result)
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Batch VIN validation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/suggest-corrections', methods=['POST'])
@rate_limit(limit=50, per=60)
def suggest_corrections():
    """
    Suggest corrections for an invalid VIN
    
    Request body:
    {
        "vin": "JTEGD34V00012I456"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'vin' not in data:
            return jsonify({
                'success': False,
                'error': 'vin is required'
            }), 400
        
        vin = data['vin']
        suggestions = vin_validator.suggest_corrections(vin)
        
        return jsonify({
            'success': True,
            'data': {
                'original_vin': vin,
                'suggestions': suggestions
            }
        })
        
    except Exception as e:
        logger.error(f"Correction suggestion error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/extract', methods=['POST'])
@rate_limit(limit=10, per=60)
def extract_vin():
    """
    Extract VIN from image using OpenAI Vision
    
    Request body:
    {
        "image_url": "https://example.com/vehicle.jpg"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'image_url' not in data:
            return jsonify({
                'success': False,
                'error': 'image_url is required'
            }), 400
        
        image_url = data['image_url']
        
        # Extract VIN
        result = vin_ocr.extract_vin_from_image(image_url)
        
        # Validate if VIN found
        if result.get('extracted') and result.get('vin'):
            vin = result['vin']
            validation = vin_validator.validate(vin)
            result['validation'] = validation
            
            # If valid, get vehicle details
            if validation.get('valid'):
                car_data = car_api.decode_vin(vin)
                if 'error' not in car_data:
                    result['vehicle_details'] = {
                        'make': car_data.get('make', ''),
                        'model': car_data.get('model', ''),
                        'year': car_data.get('year', ''),
                        'engine': car_data.get('engine', '')
                    }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"VIN extraction error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/decode/<vin>', methods=['GET'])
@rate_limit(limit=50, per=60)
def decode_vin(vin):
    """
    Decode VIN and get vehicle details
    
    Requires valid VIN
    """
    try:
        # Validate VIN first
        validation = vin_validator.validate(vin)
        
        if not validation.get('valid'):
            return jsonify({
                'success': False,
                'error': 'Invalid VIN',
                'validation': validation
            }), 400
        
        # Get vehicle details
        car_data = car_api.decode_vin(vin)
        
        if 'error' in car_data:
            return jsonify({
                'success': False,
                'error': 'VIN not found in database'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'vin': vin,
                'validation': validation,
                'vehicle': car_data
            }
        })
        
    except Exception as e:
        logger.error(f"VIN decode error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/generate-check-digit', methods=['POST'])
@rate_limit(limit=50, per=60)
def generate_check_digit():
    """
    Generate check digit for a VIN without it
    
    Request body:
    {
        "vin_without_check": "JTEGD34V00012345"  # 16 characters
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'vin_without_check' not in data:
            return jsonify({
                'success': False,
                'error': 'vin_without_check is required'
            }), 400
        
        vin_without = data['vin_without_check']
        
        # Validate length
        if len(vin_without) != 16:
            return jsonify({
                'success': False,
                'error': 'VIN without check digit must be 16 characters'
            }), 400
        
        check_digit = vin_validator.generate_check_digit(vin_without)
        
        return jsonify({
            'success': True,
            'data': {
                'check_digit': check_digit,
                'full_vin': vin_without[:8] + check_digit + vin_without[8:]
            }
        })
        
    except Exception as e:
        logger.error(f"Check digit generation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
