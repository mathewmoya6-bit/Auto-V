# api/routes/intelligence.py - AI Intelligence Routes
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from services.supabase_client import get_supabase
from services.openai_service import openai_service
from services.carapi_service import car_api
from services.vin_validator import vin_validator
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

intelligence_bp = Blueprint('intelligence', __name__)

# ─── MARKET ANALYSIS ───────────────────────────────────────────

@intelligence_bp.route('/market-analysis', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def market_analysis():
    """Get AI-powered market analysis"""
    try:
        data = request.get_json()
        
        if not data or 'vin' not in data:
            return jsonify({
                'success': False,
                'error': 'vin is required'
            }), 400
        
        vin = data['vin'].upper().strip()
        
        if not vin_validator.is_valid(vin):
            return jsonify({'success': False, 'error': 'Invalid VIN format'}), 400
        
        # Get vehicle details
        vehicle = car_api.decode_vin(vin)
        
        if 'error' in vehicle:
            return jsonify({
                'success': False,
                'error': 'Vehicle not found'
            }), 404
        
        # Get AI analysis
        analysis = openai_service.market_analysis(vehicle)
        
        return jsonify({
            'success': True,
            'data': {
                'vin': vin,
                'vehicle': vehicle,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
    except Exception as e:
        logger.error(f"Market analysis error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── PRICE PREDICTION ──────────────────────────────────────────

@intelligence_bp.route('/predict-price', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def predict_price():
    """Predict vehicle price using AI"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Get AI price prediction
        prediction = openai_service.predict_price(data)
        
        return jsonify({
            'success': True,
            'data': prediction,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Price prediction error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── DAMAGE DETECTION ──────────────────────────────────────────

@intelligence_bp.route('/detect-damage', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def detect_damage():
    """Detect damage in vehicle images using AI"""
    try:
        data = request.get_json()
        
        if not data or 'image_urls' not in data:
            return jsonify({
                'success': False,
                'error': 'image_urls is required'
            }), 400
        
        image_urls = data['image_urls']
        if not isinstance(image_urls, list):
            return jsonify({
                'success': False,
                'error': 'image_urls must be an array'
            }), 400
        
        # Process images
        results = []
        for url in image_urls:
            detection = openai_service.detect_damage(url)
            results.append({
                'image_url': url,
                'detection': detection
            })
        
        return jsonify({
            'success': True,
            'data': {
                'results': results,
                'total_images': len(results),
                'damage_detected': any(r['detection'].get('damage_detected', False) for r in results)
            },
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Damage detection error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── CHAT ──────────────────────────────────────────────────────

@intelligence_bp.route('/chat', methods=['POST'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def chat():
    """AI Chat Assistant"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'message is required'
            }), 400
        
        context = data.get('context', {})
        response = openai_service.chat(data['message'], context)
        
        return jsonify({
            'success': True,
            'data': {
                'response': response,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── RECOMMENDATIONS ──────────────────────────────────────────

@intelligence_bp.route('/recommendations', methods=['POST'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def get_recommendations():
    """Get vehicle recommendations"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        preferences = data.get('preferences', {})
        recommendations = openai_service.get_recommendations(preferences)
        
        return jsonify({
            'success': True,
            'data': recommendations,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Recommendations error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
