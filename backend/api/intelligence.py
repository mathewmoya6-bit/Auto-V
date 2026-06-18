from flask import Blueprint, request, jsonify
from api.auth_middleware import require_auth

intelligence_bp = Blueprint('intelligence', __name__)

@intelligence_bp.route('/market-trends', methods=['GET'])
@require_auth
def market_trends(user):
    return jsonify({
        'trends': {
            'Toyota': 'Stable',
            'Nissan': 'Declining',
            'Mercedes': 'Rising'
        },
        'average_values': {'Toyota Axio': 2800000}
    }), 200

@intelligence_bp.route('/vin-decode', methods=['POST'])
@require_auth
def vin_decode(user):
    vin = request.json.get('vin')
    if not vin:
        return jsonify({'error': 'VIN required'}), 400
    # Mock VIN decode
    return jsonify({
        'vin': vin,
        'make': 'Toyota',
        'model': 'Axio',
        'year': 2020,
        'engine': '1500cc',
        'country': 'Japan'
    }), 200
