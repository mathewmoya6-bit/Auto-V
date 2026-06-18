from flask import Blueprint, request, jsonify

webhooks_bp = Blueprint('webhooks', __name__)

@webhooks_bp.route('/payment-confirmation', methods=['POST'])
def payment_confirmation():
    data = request.get_json()
    # Process the webhook (e.g., update order status)
    return jsonify({'received': True}), 200
