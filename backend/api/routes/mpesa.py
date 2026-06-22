# api/routes/mpesa.py - M-Pesa API Routes (Production Ready)

import os
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, make_response

from services.mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    query_payment_status,
    verify_payment_with_mpesa,
    auto_confirm_payment,
    is_mpesa_configured,
    get_mpesa_token
)
from services.supabase_client import (
    get_supabase_client,
    get_payment_by_checkout_id,
    update_payment,
    get_user_payments,
    get_payments_by_status,
    get_payment_stats,
    get_payment_by_id
)

logger = logging.getLogger(__name__)

# ─── Create Blueprint ──────────────────────────────────────────
mpesa_bp = Blueprint('mpesa', __name__)

# ─── Configuration ──────────────────────────────────────────────
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
MPESA_ENV = os.getenv('MPESA_ENV', 'production')


# ─── Routes ──────────────────────────────────────────────────────

@mpesa_bp.route('/initiate', methods=['OPTIONS', 'POST'])
def initiate_payment():
    """Initiate M-Pesa STK Push payment"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response
    
    try:
        data = request.get_json()
        
        if not data:
            logger.error("❌ No data provided")
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        logger.info(f"📦 PAYLOAD RECEIVED: {data}")
        
        required = ['phone', 'amount']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        payment_id = data.get('payment_id') or f"PAY-{uuid.uuid4().hex[:8].upper()}"
        reference = data.get('reference') or f"AUTO-{uuid.uuid4().hex[:8].upper()}"
        
        phone = data['phone']
        if not phone or len(phone) < 10:
            return jsonify({
                'success': False,
                'error': 'Invalid phone number'
            }), 400
        
        amount = data['amount']
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except:
            return jsonify({
                'success': False,
                'error': 'Amount must be a positive number'
            }), 400
        
        logger.info(f"📝 Processing payment: {payment_id} for {phone} - KES {amount}")
        
        result = initiate_stk_push(
            phone=phone,
            amount=amount,
            payment_id=payment_id,
            service=data.get('service', 'AUTO-V'),
            reference=reference,
            user_id=data.get('user_id'),
            request_id=data.get('request_id')
        )
        
        return jsonify({
            'success': True,
            'data': {
                'payment_id': payment_id,
                'checkout_request_id': result.get('checkout_request_id'),
                'merchant_request_id': result.get('merchant_request_id'),
                'reference': reference,
                'message': 'STK Push sent successfully'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ M-Pesa initiate error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mpesa_bp.route('/status/<payment_id>', methods=['GET'])
def get_payment_status(payment_id):
    """Get payment status"""
    try:
        payment = get_payment_by_id(payment_id)
        
        if not payment:
            payment = get_payment_by_checkout_id(payment_id)
        
        if not payment:
            return jsonify({
                'success': True,
                'payment_id': payment_id,
                'status': 'not_found',
                'message': 'Payment not found'
            }), 200
        
        return jsonify({
            'success': True,
            'payment_id': payment.get('id'),
            'checkout_request_id': payment.get('checkout_request_id'),
            'status': payment.get('status'),
            'amount': payment.get('amount'),
            'mpesa_code': payment.get('mpesa_code'),
            'mpesa_result_code': payment.get('mpesa_result_code'),
            'mpesa_result_desc': payment.get('mpesa_result_desc'),
            'paid_at': payment.get('paid_at'),
            'created_at': payment.get('created_at')
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mpesa_bp.route('/verify/<checkout_id>', methods=['POST'])
def verify_payment(checkout_id):
    """Verify payment with M-Pesa API"""
    try:
        result = verify_payment_with_mpesa(checkout_id)
        
        if result.get('verified'):
            return jsonify({
                'success': True,
                'status': 'completed',
                'receipt': result.get('receipt'),
                'amount': result.get('amount'),
                'phone': result.get('phone')
            }), 200
        else:
            return jsonify({
                'success': False,
                'status': result.get('status', 'failed'),
                'result_code': result.get('result_code'),
                'result_desc': result.get('result_desc')
            }), 200
            
    except Exception as e:
        logger.error(f"❌ Verify payment error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mpesa_bp.route('/auto-confirm/<payment_id>', methods=['POST'])
def auto_confirm(payment_id):
    """Auto-confirm payment by verifying with M-Pesa API"""
    try:
        result = auto_confirm_payment(payment_id)
        return jsonify(result), 200 if result.get('success') else 400
        
    except Exception as e:
        logger.error(f"❌ Auto-confirm error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@mpesa_bp.route('/user/<user_id>', methods=['GET'])
def get_user_payments_route(user_id):
    """Get all payments for a user"""
    try:
        limit = request.args.get('limit', 50, type=int)
        payments = get_user_payments(user_id, limit)
        
        return jsonify({
            'success': True,
            'data': payments,
            'count': len(payments)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Get user payments error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mpesa_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get payment statistics"""
    try:
        stats = get_payment_stats()
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Get stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mpesa_bp.route('/test', methods=['GET'])
def test_mpesa():
    """Test endpoint to verify M-Pesa routes are working."""
    return jsonify({
        'success': True,
        'message': 'M-Pesa routes are working!',
        'shortcode': MPESA_SHORTCODE,
        'environment': MPESA_ENV,
        'timestamp': datetime.now().isoformat()
    }), 200


@mpesa_bp.route('/health', methods=['GET'])
def mpesa_health():
    """M-Pesa service health check."""
    status = {
        'service': 'mpesa',
        'status': 'healthy',
        'environment': MPESA_ENV,
        'shortcode': MPESA_SHORTCODE,
        'configured': is_mpesa_configured()
    }
    
    try:
        token = get_mpesa_token()
        status['token_available'] = bool(token)
        if not token:
            status['status'] = 'degraded'
    except Exception as e:
        status['token_available'] = False
        status['error'] = str(e)
        status['status'] = 'degraded'
    
    return jsonify(status), 200


# ============================================================
# ✅ FIX: M-PESA CALLBACK ROUTE (Now in Blueprint)
# ============================================================

@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback_route():
    """
    M-Pesa callback endpoint (receives payment confirmation from Safaricom).
    ✅ FIX: Properly handles Safaricom payload with safety checks
    ✅ FIX: Always returns 200 to Safaricom
    ✅ FIX: Validates structure before processing
    """
    try:
        # Log the raw request for debugging
        logger.info("=" * 60)
        logger.info("📞 M-Pesa callback received")
        
        # Get the raw JSON data
        callback_data = request.get_json()
        logger.info(f"📥 Raw callback data: {callback_data}")
        
        # ✅ FIX: Validate callback structure
        if not callback_data:
            logger.error("❌ No JSON data in callback")
            return jsonify({"ResultCode": 1, "ResultDesc": "No data"}), 200
        
        # ✅ FIX: Safely check for stkCallback using .get()
        body = callback_data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        if not stk_callback:
            logger.error("❌ Missing stkCallback in payload")
            logger.info(f"📥 Received structure: {callback_data.keys()}")
            return jsonify({"ResultCode": 1, "ResultDesc": "Missing stkCallback"}), 200
        
        logger.info(f"📊 stkCallback: {stk_callback}")
        
        # Process the callback with the handler
        result = handle_mpesa_callback(callback_data)
        logger.info(f"✅ Callback processed: {result}")
        
        # ✅ FIX: Always return 200 to Safaricom
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"❌ M-Pesa callback error: {str(e)}", exc_info=True)
        # ✅ FIX: Always return 200 even on error
        return jsonify({"ResultCode": 1, "ResultDesc": str(e)}), 200
