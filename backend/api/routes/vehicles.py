# api/routes/vehicles.py - Vehicle Routes with CarAPI Integration
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from services.carapi_service import get_carapi_service
from services.vin_validator import vin_validator
from services.supabase_client import get_supabase
from services.valuation_service import get_valuation_service
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

vehicles_bp = Blueprint('vehicles', __name__)

# ─── DECODE VIN ──────────────────────────────────────────────

@vehicles_bp.route('/decode-vin', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def decode_vin():
    """
    Decode VIN using CarAPI
    """
    try:
        data = request.get_json()
        
        if not data or 'vin' not in data:
            return jsonify({
                'success': False,
                'error': 'vin is required'
            }), 400
        
        vin = data['vin'].upper().strip()
        
        # Validate VIN format
        if not vin_validator.is_valid(vin):
            return jsonify({
                'success': False,
                'error': 'Invalid VIN format'
            }), 400
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.decode_vin(vin)
        
        if "error" in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        # Also check if vehicle exists in our database
        supabase = get_supabase()
        existing = supabase.get_vehicle_by_vin(vin)
        
        return jsonify({
            'success': True,
            'data': {
                'vehicle': result,
                'in_database': bool(existing),
                'database_vehicle': existing[0] if existing else None
            },
            'source': 'CarAPI'
        }), 200
        
    except Exception as e:
        logger.error(f"VIN decode error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── GET VALUATION ───────────────────────────────────────────

@vehicles_bp.route('/valuation', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def get_valuation():
    """
    Get vehicle valuation using CarAPI
    """
    try:
        data = request.get_json()
        
        if not data or 'vin' not in data:
            return jsonify({
                'success': False,
                'error': 'vin is required'
            }), 400
        
        vin = data['vin'].upper().strip()
        
        # Validate VIN format
        if not vin_validator.is_valid(vin):
            return jsonify({
                'success': False,
                'error': 'Invalid VIN format'
            }), 400
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.get_valuation(vin)
        
        if "error" in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        # Also get our own valuation for comparison
        valuation_service = get_valuation_service()
        our_valuation = valuation_service.calculate_valuation({
            'vin': vin,
            'make': data.get('make'),
            'model': data.get('model'),
            'year': data.get('year'),
            'odometer': data.get('odometer', 0),
            'condition': data.get('condition', 'Good'),
            'purpose': data.get('purpose', 'Market Value'),
            'region': data.get('region', 'Nairobi')
        })
        
        return jsonify({
            'success': True,
            'data': {
                'carapi_valuation': result,
                'auto_v_valuation': our_valuation,
                'comparison': {
                    'market_value_carapi': result.get('valuation', {}).get('current_value'),
                    'market_value_autov': our_valuation.get('market_value'),
                    'difference': abs(
                        (result.get('valuation', {}).get('current_value', 0) or 0) - 
                        (our_valuation.get('market_value', 0) or 0)
                    )
                }
            },
            'source': 'CarAPI + AUTO-V'
        }), 200
        
    except Exception as e:
        logger.error(f"Valuation error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── SEARCH VEHICLES ────────────────────────────────────────

@vehicles_bp.route('/search', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def search_vehicles():
    """
    Search for vehicles using CarAPI
    """
    try:
        make = request.args.get('make')
        model = request.args.get('model')
        year = request.args.get('year', type=int)
        
        if not make and not model:
            return jsonify({
                'success': False,
                'error': 'At least make or model is required'
            }), 400
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.search_vehicles(make, model, year)
        
        if "error" in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result.get('vehicles', [])),
            'source': 'CarAPI'
        }), 200
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── GET VEHICLE PHOTOS ─────────────────────────────────────

@vehicles_bp.route('/photos', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def get_vehicle_photos():
    """
    Get vehicle photos using CarAPI
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('make') or not data.get('model'):
            return jsonify({
                'success': False,
                'error': 'make and model are required'
            }), 400
        
        make = data['make']
        model = data['model']
        year = data.get('year')
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.get_vehicle_photos(make, model, year)
        
        if "error" in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        return jsonify({
            'success': True,
            'data': result,
            'source': 'CarAPI'
        }), 200
        
    except Exception as e:
        logger.error(f"Photos error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── STOLEN VEHICLE CHECK ──────────────────────────────────

@vehicles_bp.route('/stolen-check', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def check_stolen_vehicle():
    """
    Check if vehicle has been reported stolen
    """
    try:
        data = request.get_json()
        
        if not data or 'vin' not in data:
            return jsonify({
                'success': False,
                'error': 'vin is required'
            }), 400
        
        vin = data['vin'].upper().strip()
        
        # Validate VIN format
        if not vin_validator.is_valid(vin):
            return jsonify({
                'success': False,
                'error': 'Invalid VIN format'
            }), 400
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.check_stolen_vehicle(vin)
        
        if "error" in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        return jsonify({
            'success': True,
            'data': result,
            'source': 'CarAPI'
        }), 200
        
    except Exception as e:
        logger.error(f"Stolen check error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── GET RECALLS ────────────────────────────────────────────

@vehicles_bp.route('/recalls', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def get_recalls():
    """
    Get vehicle recall records
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('make') or not data.get('model'):
            return jsonify({
                'success': False,
                'error': 'make and model are required'
            }), 400
        
        make = data['make']
        model = data['model']
        year = data.get('year')
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.get_recalls(make, model, year)
        
        if "error" in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        return jsonify({
            'success': True,
            'data': result,
            'source': 'CarAPI'
        }), 200
        
    except Exception as e:
        logger.error(f"Recalls error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── PLATE TO VIN ───────────────────────────────────────────

@vehicles_bp.route('/plate-to-vin', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def plate_to_vin():
    """
    Convert license plate to VIN
    """
    try:
        data = request.get_json()
        
        if not data or 'plate' not in data:
            return jsonify({
                'success': False,
                'error': 'plate is required'
            }), 400
        
        plate = data['plate'].upper().strip()
        country = data.get('country', 'us')
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.plate_to_vin(plate, country)
        
        if "error" in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        return jsonify({
            'success': True,
            'data': result,
            'source': 'CarAPI'
        }), 200
        
    except Exception as e:
        logger.error(f"Plate to VIN error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── VEHICLE STATS ──────────────────────────────────────────

@vehicles_bp.route('/stats', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_vehicle_stats():
    """
    Get vehicle statistics
    """
    try:
        supabase = get_supabase()
        carapi = get_carapi_service()
        
        # Get database stats
        db_stats = supabase.get_stats()
        
        # Get CarAPI stats
        carapi_stats = carapi.get_stats()
        
        return jsonify({
            'success': True,
            'data': {
                'database': db_stats,
                'carapi': carapi_stats,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Stats error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── AUTO-FILL FROM VIN ─────────────────────────────────────

@vehicles_bp.route('/auto-fill', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def auto_fill_from_vin():
    """
    Auto-fill vehicle details from VIN
    """
    try:
        data = request.get_json()
        
        if not data or 'vin' not in data:
            return jsonify({
                'success': False,
                'error': 'vin is required'
            }), 400
        
        vin = data['vin'].upper().strip()
        
        # Validate VIN format
        if not vin_validator.is_valid(vin):
            return jsonify({
                'success': False,
                'error': 'Invalid VIN format'
            }), 400
        
        # Get CarAPI service
        carapi = get_carapi_service()
        result = carapi.decode_vin(vin)
        
        if "error" in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        # Format for AUTO-V
        vehicle_data = {
            'vin': vin,
            'make': result.get('make', ''),
            'model': result.get('model', ''),
            'year': result.get('year'),
            'engine_cc': result.get('engine_cc') or result.get('engine', {}).get('displacement'),
            'transmission': result.get('transmission_type') or result.get('transmission'),
            'fuel_type': result.get('fuel_type'),
            'body_type': result.get('body_type') or result.get('body_style'),
            'drive_type': result.get('drive_type'),
            'doors': result.get('doors'),
            'horsepower': result.get('horsepower') or result.get('engine', {}).get('horsepower'),
            'torque': result.get('torque') or result.get('engine', {}).get('torque'),
            'cylinders': result.get('engine', {}).get('cylinders'),
            'weight': result.get('weight'),
            'color': result.get('color', ''),
            'specs': result
        }
        
        return jsonify({
            'success': True,
            'data': vehicle_data,
            'source': 'CarAPI'
        }), 200
        
    except Exception as e:
        logger.error(f"Auto-fill error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
