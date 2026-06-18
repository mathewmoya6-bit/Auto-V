import uuid
import logging
from flask import Blueprint, request, jsonify
from services.mpesa import initiate_stk_push, handle_mpesa_callback
from services.supabase_client import get_supabase
from api.auth_middleware import require_auth

logger = logging.getLogger(__name__)
payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/initiate', methods=['POST'])
@require_auth
def initiate_payment(user):
    data = request.get_json()
    logger.info(f"Payment initiation request from user {user.id}")

    # ─── Validation ────────────────────────────────────────
    phone = data.get('phone')
    amount = data.get('amount')
    service_type = data.get('service_type', 'valuation')
    reference = data.get('reference') or f"AUTO-{uuid.uuid4().hex[:8].upper()}"

    if not phone:
        return jsonify({'error': 'Phone number required'}), 400
    if not amount or amount <= 0:
        return jsonify({'error': 'Valid amount required'}), 400
    if len(phone) < 10:
        return jsonify({'error': 'Invalid phone number format'}), 400

    # ─── Create payment record ────────────────────────────
    supabase = get_supabase()
    payment_data = {
        'user_id': user.id,
        'service_type': service_type,
        'amount': amount,
        'payment_method': 'mpesa',
        'status': 'pending',
        'reference': reference,
        'mpesa_phone': phone,
        'created_at': 'now()'
    }
    result = supabase.table('payments').insert(payment_data).execute()
    if not result.data:
        logger.error("Failed to create payment record")
        return jsonify({'error': 'Failed to create payment'}), 500
    payment = result.data[0]

    # ─── Initiate STK Push ────────────────────────────────
    try:
        stk_response = initiate_stk_push(
            phone=phone,
            amount=amount,
            payment_id=payment['id'],
            reference=reference,
            service=service_type
        )
        supabase.table('payments').update({
            'mpesa_checkout_id': stk_response.get('CheckoutRequestID')
        }).eq('id', payment['id']).execute()

        logger.info(f"STK Push sent for payment {payment['id']}")
        return jsonify({
            'success': True,
            'payment_id': payment['id'],
            'checkout_id': stk_response.get('CheckoutRequestID'),
            'message': 'STK Push sent'
        }), 200
    except Exception as e:
        logger.error(f"STK Push failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@payments_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json()
    logger.info("M-Pesa callback received")
    try:
        handle_mpesa_callback(data)
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Error'}), 500

@payments_bp.route('/status/<payment_id>', methods=['GET'])
def get_payment_status(payment_id):
    supabase = get_supabase()
    result = supabase.table('payments').select('*').eq('id', payment_id).execute()
    if not result.data:
        return jsonify({'error': 'Payment not found'}), 404
    return jsonify(result.data[0]), 200
