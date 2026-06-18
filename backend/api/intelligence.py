from flask import Blueprint, request, jsonify

intelligence_bp = Blueprint('intelligence', __name__)

@intelligence_bp.route('/market-trends', methods=['GET'])
def market_trends():
    return jsonify({
        'trends': {
            'Toyota': 'Stable',
            'Nissan': 'Declining',
            'Mercedes': 'Rising'
        },
        'average_values': {'Toyota Axio': 2800000}
    }), 200

@intelligence_bp.route('/vin-decode', methods=['POST'])
def vin_decode():
    vin = request.json.get('vin')
    if not vin:
        return jsonify({'error': 'VIN required'}), 400
    return jsonify({
        'vin': vin,
        'make': 'Toyota',
        'model': 'Axio',
        'year': 2020,
        'engine': '1500cc',
        'country': 'Japan'
    }), 200
