# api/routes/payments.py - Payment Routes
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import uuid

from services.supabase_client import get_supabase
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

payments_bp = Blueprint('payments', __name__)

# ─── PAYMENT METHODS ────────────────────────────────────────────

@payments_bp.route('/methods', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_payment_methods():
    """Get available payment methods"""
    try:
        methods = [
            {
                'id': 'mpesa',
                'name': 'M-Pesa',
                'logo': '/images/mpesa.png',
                'is_active': True
            },
            {
                'id': 'card',
                'name': 'Card Payment',
                'logo': '/images/card.png',
                'is_active': False
            },
            {
                'id': 'bank',
                'name': 'Bank Transfer',
                'logo': '/images/bank.png',
                'is_active': False
            }
        ]
        
        return jsonify({
            'success': True,
            'data': methods
        }), 200
    except Exception as e:
        logger.error(f"Get payment methods error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── INITIATE PAYMENT ──────────────────────────────────────────

@payments_bp.route('/initiate', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def initiate_payment():
    """Initiate a payment"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required = ['amount', 'service_type', 'payment_method']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing fields: {", ".join(missing)}'
            }), 400
        
        # Generate payment reference
        reference = f"PAY-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Save payment record
        supabase = get_supabase()
        result = supabase.save_payment({
            'reference': reference,
            'amount': data['amount'],
            'service_type': data['service_type'],
            'payment_method': data['payment_method'],
            'service_id': data.get('service_id'),
            'status': 'pending',
            'user_id': request.user_id,
            'created_at': datetime.now().isoformat()
        })
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to initiate payment')
            }), 500
        
        # If M-Pesa, initiate STK Push
        if data['payment_method'] == 'mpesa':
            from .mpesa import stk_push
            phone_number = data.get('phone_number')
            
            if not phone_number:
                return jsonify({
                    'success': False,
                    'error': 'phone_number is required for M-Pesa'
                }), 400
            
            mpesa_result = stk_push(
                phone_number=phone_number,
                amount=data['amount'],
                account_reference=reference,
                transaction_desc=f"AUTO-V {data['service_type']}"
            )
            
            if not mpesa_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': mpesa_result.get('error', 'M-Pesa initiation failed')
                }), 500
            
            # Update payment with checkout ID
            supabase.update_payment(reference, {
                'checkout_request_id': mpesa_result.get('checkout_request_id'),
                'status': 'pending'
            })
        
        return jsonify({
            'success': True,
            'data': {
                'reference': reference,
                'status': 'pending',
                'message': 'Payment initiated successfully'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Initiate payment error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── PAYMENT STATUS ────────────────────────────────────────────

@payments_bp.route('/<reference>', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_payment_status(reference):
    """Get payment status"""
    try:
        supabase = get_supabase()
        result = supabase.get_payment(reference)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Payment not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
    except Exception as e:
        logger.error(f"Get payment error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── PAYMENT HISTORY ───────────────────────────────────────────

@payments_bp.route('/history', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_payment_history():
    """Get user payment history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        supabase = get_supabase()
        results = supabase.get_user_payments(request.user_id, limit)
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        }), 200
    except Exception as e:
        logger.error(f"Get payment history error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── PAYMENT STATS ─────────────────────────────────────────────

@payments_bp.route('/stats', methods=['GET'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def get_payment_stats():
    """Get payment statistics"""
    try:
        supabase = get_supabase()
        stats = supabase.get_payment_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Get payment stats error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
