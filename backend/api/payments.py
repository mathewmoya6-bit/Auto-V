from flask import Blueprint, request, jsonify
from services.mpesa import initiate_stk_push, handle_mpesa_callback
from services.supabase_client import get_supabase
import uuid

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/initiate', methods=['POST'])
def initiate_payment():
    data = request.get_json()
    user_id = data.get('user_id')
    phone = data.get('phone')
    amount = data.get('amount')
    service_type = data.get('service_type', 'valuation')
    reference = data.get('reference') or f"AUTO-{uuid.uuid4().hex[:8].upper()}"

    if not user_id or not phone or not amount:
        return jsonify({'error': 'Missing required fields'}), 400

    supabase = get_supabase()
    payment_data = {
        'user_id': user_id,
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
        return jsonify({'error': 'Failed to create payment'}), 500
    payment = result.data[0]

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

        return jsonify({
            'success': True,
            'payment_id': payment['id'],
            'checkout_id': stk_response.get('CheckoutRequestID'),
            'message': 'STK Push sent'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payments_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json()
    try:
        handle_mpesa_callback(data)
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
    except Exception as e:
        print(f"Callback error: {e}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Error'}), 500

@payments_bp.route('/status/<payment_id>', methods=['GET'])
def get_payment_status(payment_id):
    supabase = get_supabase()
    result = supabase.table('payments').select('*').eq('id', payment_id).execute()
    if not result.data:
        return jsonify({'error': 'Payment not found'}), 404
    return jsonify(result.data[0]), 200
