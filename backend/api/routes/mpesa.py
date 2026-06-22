# api/routes/mpesa.py - M-Pesa API Routes (Production Ready)

import os
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

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
    get_payment_by_id,
    get_payment_by_custom_id,           # ✅ NEW: Custom payment_id lookup
    get_payment_by_checkout_id,
    update_payment,
    update_payment_by_custom_id,        # ✅ NEW: Update by custom payment_id
    get_user_payments,
    get_payments_by_status,
    get_payment_stats
)

logger = logging.getLogger(__name__)

# ─── Create Blueprint ──────────────────────────────────────────
mpesa_bp = Blueprint('mpesa', __name__)

# ─── Configuration ──────────────────────────────────────────────
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
MPESA_ENV = os.getenv('MPESA_ENV', 'production')


# ─── Helper: Standardized Response ─────────────────────────────
def standard_response(success: bool, data: dict = None, error: str = None, status: int = 200):
    """Standardized API response format."""
    response = {"success": success}
    if data is not None:
        response["data"] = data
    if error is not None:
        response["error"] = error
    return jsonify(response), status


# ─── Routes ──────────────────────────────────────────────────────

@mpesa_bp.route('/initiate', methods=['POST'])
def initiate_payment():
    """Initiate M-Pesa STK Push payment"""
    try:
        data = request.get_json()
        
        if not data:
            logger.error("❌ No data provided")
            return standard_response(False, error='No data provided', status=400)
        
        logger.info(f"📦 PAYLOAD RECEIVED: {data}")
        
        # Validate required fields
        required = ['phone', 'amount']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return standard_response(
                False, 
                error=f'Missing required fields: {", ".join(missing)}', 
                status=400
            )
        
        # Generate IDs
        payment_id = data.get('payment_id') or f"PAY-{uuid.uuid4().hex[:8].upper()}"
        reference = data.get('reference') or f"AUTO-{uuid.uuid4().hex[:8].upper()}"
        
        # Validate phone
        phone = data['phone']
        if not phone or len(phone) < 10:
            return standard_response(False, error='Invalid phone number', status=400)
        
        # Robust amount parsing
        amount = data['amount']
        try:
            amount_str = str(amount).replace(",", "").strip()
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except:
            return standard_response(False, error='Amount must be a positive number', status=400)
        
        logger.info(f"📝 Processing payment: {payment_id} for {phone} - KES {amount}")
        
        # Process payment
        result = initiate_stk_push(
            phone=phone,
            amount=amount,
            payment_id=payment_id,
            service=data.get('service', 'AUTO-V'),
            reference=reference,
            user_id=data.get('user_id'),
            request_id=data.get('request_id')
        )
        
        return standard_response(True, data={
            'payment_id': payment_id,
            'checkout_request_id': result.get('checkout_request_id'),
            'merchant_request_id': result.get('merchant_request_id'),
            'reference': reference,
            'message': 'STK Push sent successfully'
        })
        
    except Exception as e:
        logger.error(f"❌ M-Pesa initiate error: {str(e)}", exc_info=True)
        return standard_response(False, error='Payment initiation failed', status=500)


# ─── STATUS ENDPOINT ──────────────────────────────────────────────
# ✅ FIXED: Now checks both UUID and custom payment_id

@mpesa_bp.route('/status/<payment_id>', methods=['GET'])
def get_payment_status(payment_id):
    """
    Get payment status by either UUID or custom payment_id.
    
    Args:
        payment_id: Can be UUID (id) or string (payment_id)
    """
    try:
        # Try by primary key (UUID)
        payment = get_payment_by_id(payment_id)
        
        if not payment:
            # ✅ Try by custom payment_id (string like 'PAY-XXXXXX')
            payment = get_payment_by_custom_id(payment_id)
        
        if not payment:
            return standard_response(True, data={
                'payment_id': payment_id,
                'status': 'not_found',
                'message': 'Payment not found'
            })
        
        return standard_response(True, data={
            'payment_id': payment.get('payment_id'),
            'id': payment.get('id'),
            'checkout_request_id': payment.get('checkout_request_id'),
            'status': payment.get('status'),
            'amount': payment.get('amount'),
            'mpesa_code': payment.get('mpesa_code'),
            'mpesa_result_code': payment.get('mpesa_result_code'),
            'mpesa_result_desc': payment.get('mpesa_result_desc'),
            'paid_at': payment.get('paid_at'),
            'created_at': payment.get('created_at')
        })
        
    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
        return standard_response(False, error='Status check failed', status=500)


@mpesa_bp.route('/verify/<checkout_id>', methods=['POST'])
def verify_payment(checkout_id):
    """Verify payment with M-Pesa API"""
    try:
        result = verify_payment_with_mpesa(checkout_id)
        
        if result.get('verified'):
            return standard_response(True, data={
                'status': 'completed',
                'receipt': result.get('receipt'),
                'amount': result.get('amount'),
                'phone': result.get('phone')
            })
        else:
            return standard_response(False, data={
                'status': result.get('status', 'failed'),
                'result_code': result.get('result_code'),
                'result_desc': result.get('result_desc')
            })
            
    except Exception as e:
        logger.error(f"❌ Verify payment error: {str(e)}")
        return standard_response(False, error='Verification failed', status=500)


# ─── AUTO-CONFIRM ENDPOINT ──────────────────────────────────────
# ✅ FIXED: Now handles both UUID and custom payment_id

@mpesa_bp.route('/auto-confirm/<payment_id>', methods=['POST'])
def auto_confirm(payment_id):
    """
    Auto-confirm payment by verifying with M-Pesa API.
    
    Args:
        payment_id: Can be UUID (id) or string (payment_id)
    """
    try:
        # First try to find the payment
        payment = get_payment_by_id(payment_id)
        
        if not payment:
            payment = get_payment_by_custom_id(payment_id)
        
        if not payment:
            return standard_response(False, error='Payment not found', status=404)
        
        # Get the actual UUID for the payment
        actual_id = payment.get('id')
        
        # Auto-confirm using the UUID
        result = auto_confirm_payment(actual_id)
        return standard_response(result.get('success'), data=result)
        
    except Exception as e:
        logger.error(f"❌ Auto-confirm error: {str(e)}", exc_info=True)
        return standard_response(False, error='Auto-confirm failed', status=500)


@mpesa_bp.route('/user/<user_id>', methods=['GET'])
def get_user_payments_route(user_id):
    """Get all payments for a user"""
    try:
        limit = request.args.get('limit', 50, type=int)
        payments = get_user_payments(user_id, limit)
        
        return standard_response(True, data={
            'payments': payments,
            'count': len(payments)
        })
        
    except Exception as e:
        logger.error(f"❌ Get user payments error: {str(e)}")
        return standard_response(False, error='Failed to get user payments', status=500)


@mpesa_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get payment statistics"""
    try:
        stats = get_payment_stats()
        return standard_response(True, data=stats)
        
    except Exception as e:
        logger.error(f"❌ Get stats error: {str(e)}")
        return standard_response(False, error='Failed to get stats', status=500)


@mpesa_bp.route('/test', methods=['GET'])
def test_mpesa():
    """Test endpoint to verify M-Pesa routes are working."""
    return standard_response(True, data={
        'message': 'M-Pesa routes are working!',
        'shortcode': MPESA_SHORTCODE,
        'environment': MPESA_ENV,
        'timestamp': datetime.now().isoformat()
    })


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
# ✅ M-PESA CALLBACK ROUTE
# ============================================================

@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback_route():
    """
    M-Pesa callback endpoint (receives payment confirmation from Safaricom).
    ✅ FIX: Silent JSON parsing
    ✅ FIX: Proper None check for stkCallback
    ✅ FIX: Safe error messages
    ✅ FIX: Always returns 200 to Safaricom
    """
    try:
        logger.info("=" * 60)
        logger.info("📞 M-Pesa callback received")
        
        # Silent JSON parsing (won't crash on malformed JSON)
        callback_data = request.get_json(silent=True)
        
        # Log only that we received something (mask sensitive data)
        logger.info("📥 Callback received (payload hidden for security)")
        
        # Validate callback data
        if not callback_data:
            logger.error("❌ No JSON data in callback")
            return jsonify({"ResultCode": 1, "ResultDesc": "No data"}), 200
        
        # Check for stkCallback with proper None check
        body = callback_data.get('Body')
        if not body:
            logger.error("❌ Missing Body in callback")
            return jsonify({"ResultCode": 1, "ResultDesc": "Missing Body"}), 200
        
        stk_callback = body.get('stkCallback')
        
        # Proper None check (not truthy check on empty dict)
        if stk_callback is None:
            logger.error("❌ Missing stkCallback in payload")
            logger.info(f"📥 Received structure keys: {body.keys()}")
            return jsonify({"ResultCode": 1, "ResultDesc": "Missing stkCallback"}), 200
        
        logger.info(f"📊 ResultCode: {stk_callback.get('ResultCode')}")
        logger.info(f"📊 CheckoutID: {stk_callback.get('CheckoutRequestID')}")
        
        # Process the callback
        result = handle_mpesa_callback(callback_data)
        logger.info(f"✅ Callback processed: {result}")
        
        # Always return 200 to Safaricom
        return jsonify(result), 200
        
    except Exception as e:
        # Log the real error but return safe message
        logger.error(f"❌ M-Pesa callback error: {str(e)}", exc_info=True)
        return jsonify({
            "ResultCode": 1,
            "ResultDesc": "System error"
        }), 200


# ============================================================
# ✅ FORCE COMPLETE ROUTE (Manual confirmation)
# ============================================================

@mpesa_bp.route('/force-complete/<payment_id>', methods=['POST'])
def force_complete_payment(payment_id):
    """
    Force complete a payment manually (admin use only).
    
    Args:
        payment_id: Can be UUID (id) or string (payment_id)
        
    Request body:
        {
            "transaction_id": "QWERTY123"
        }
    """
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id') if data else None
        
        if not transaction_id:
            return standard_response(False, error='Transaction ID is required', status=400)
        
        logger.info(f"📝 Force completing payment: {payment_id} with transaction: {transaction_id}")
        
        # Find the payment
        payment = get_payment_by_id(payment_id)
        
        if not payment:
            payment = get_payment_by_custom_id(payment_id)
        
        if not payment:
            return standard_response(False, error='Payment not found', status=404)
        
        actual_id = payment.get('id')
        
        # Update payment
        result = update_payment(actual_id, {
            'status': 'completed',
            'transaction_id': transaction_id,
            'mpesa_code': transaction_id,
            'payment_data': {'transaction_id': transaction_id, 'manual_confirm': True},
            'paid_at': datetime.now().isoformat()
        })
        
        if result.get('success'):
            return standard_response(True, data={
                'message': 'Payment confirmed successfully',
                'payment_id': payment_id,
                'transaction_id': transaction_id
            })
        else:
            return standard_response(False, error='Failed to update payment', status=500)
        
    except Exception as e:
        logger.error(f"❌ Force complete error: {str(e)}", exc_info=True)
        return standard_response(False, error='Force complete failed', status=500)
