# api/routes/mpesa.py - M-Pesa Routes (Production Ready)

import os
import logging
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

# ─── FIXED: Import from the correct location ──────────────────
# Use the services/supabase_client.py
from services.supabase_client import get_supabase_client as get_supabase

from services.mpesa import (
    initiate_stk_push,
    query_payment_status,
    is_mpesa_configured,
    get_mpesa_token,
    handle_mpesa_callback,
    sanitize_log_data,
    normalize_phone
)

logger = logging.getLogger(__name__)

# ─── Blueprint ──────────────────────────────────────────────────
mpesa_bp = Blueprint('mpesa', __name__)


# ─── =========================================================───
# ─── ROUTE: INITIATE PAYMENT ──────────────────────────────────
# ─── =========================================================───

@mpesa_bp.route('/initiate', methods=['POST', 'OPTIONS'])
def initiate_payment():
    """Initiate M-Pesa STK Push payment."""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json()
        logger.info("📥 Payment initiation request received")
        
        if data:
            sanitized = sanitize_log_data(data)
            logger.info(f"Request data: {json.dumps(sanitized, indent=2)}")

        # ─── Validate required fields ──────────────────────────
        required = ['phone', 'amount', 'service', 'purpose']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        phone = data.get('phone')
        amount = float(data.get('amount'))
        service = data.get('service')
        purpose = data.get('purpose')
        client_type = data.get('client_type', 'individual')
        reference = data.get('reference')

        # ─── Validate amount ─────────────────────────────────────
        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400

        amount_int = int(round(amount))
        if amount_int < 1:
            return jsonify({'error': 'Amount must be at least 1 KES'}), 400

        # ─── Validate phone ──────────────────────────────────────
        try:
            normalized_phone = normalize_phone(phone)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        # ─── Check M-Pesa configuration ──────────────────────────
        if not is_mpesa_configured():
            logger.error("❌ M-Pesa not configured")
            return jsonify({
                'error': 'M-Pesa is not configured. Please contact support.',
                'code': 'MPESA_NOT_CONFIGURED'
            }), 503

        # ─── Get user from auth ──────────────────────────────────
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                from api.auth_middleware import get_user_from_token
                token = auth_header.split(' ')[1]
                user_data = get_user_from_token(token)
                if user_data:
                    user_id = user_data.get('id')
            except Exception as e:
                logger.warning(f"Could not get user from token: {e}")

        # ─── Get Supabase client ──────────────────────────────────
        supabase = get_supabase()

        # ─── Create payment record ──────────────────────────────
        payment_id = str(uuid.uuid4())
        payment_data = {
            'id': payment_id,
            'user_id': user_id,
            'service_type': service,
            'purpose': purpose,
            'amount': amount_int,
            'phone': normalized_phone,
            'client_type': client_type,
            'status': 'pending',
            'reference': reference or f'AUTO-{payment_id[:8].upper()}',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        payment_response = supabase.table('payments').insert(payment_data).execute()

        if not payment_response.data:
            logger.error(f"❌ Failed to create payment record")
            return jsonify({'error': 'Failed to create payment record'}), 500

        payment = payment_response.data[0]
        payment_id = payment['id']
        logger.info(f"✅ Created payment: {payment_id}")

        # ─── Initiate STK Push ──────────────────────────────────
        try:
            mpesa_response = initiate_stk_push(
                phone=phone,
                amount=float(amount_int),
                payment_id=payment_id,
                service=service,
                reference=reference
            )

            checkout_id = mpesa_response.get('CheckoutRequestID')
            merchant_request_id = mpesa_response.get('MerchantRequestID')

            if not checkout_id:
                logger.error(f"❌ No CheckoutRequestID for payment {payment_id}")
                supabase.table('payments').update({
                    'status': 'failed',
                    'mpesa_result_desc': 'No CheckoutRequestID from M-Pesa'
                }).eq('id', payment_id).execute()
                return jsonify({
                    'error': 'Failed to initiate STK Push. Please try again.',
                    'payment_id': payment_id
                }), 400

            # ─── Update payment with checkout ID ──────────────────
            supabase.table('payments').update({
                'checkout_request_id': checkout_id,
                'merchant_request_id': merchant_request_id,
                'updated_at': datetime.now().isoformat()
            }).eq('id', payment_id).execute()

            logger.info(f"✅ STK Push sent for payment {payment_id}, CheckoutID: {checkout_id}")

            return jsonify({
                'success': True,
                'payment_id': payment_id,
                'checkout_id': checkout_id,
                'merchant_request_id': merchant_request_id,
                'reference': reference,
                'status': 'pending',
                'message': 'STK Push sent to your phone. Please confirm the transaction.',
                'amount': amount_int,
                'phone': normalized_phone
            }), 200

        except Exception as e:
            supabase.table('payments').update({
                'status': 'failed',
                'mpesa_result_desc': str(e),
                'failed_at': datetime.now().isoformat()
            }).eq('id', payment_id).execute()

            logger.error(f"❌ STK Push failed for payment {payment_id}: {e}")
            return jsonify({
                'error': str(e),
                'payment_id': payment_id,
                'reference': reference
            }), 400

    except ValueError as e:
        return jsonify({'error': f'Invalid value: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"❌ Payment initiation error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── =========================================================───
# ─── ROUTE: GET PAYMENT STATUS ─────────────────────────────────
# ─── =========================================================───

@mpesa_bp.route('/status/<payment_id>', methods=['GET', 'OPTIONS'])
def get_payment_status(payment_id):
    """Get payment status."""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        supabase = get_supabase()

        response = supabase.table('payments')\
            .select('*')\
            .eq('id', payment_id)\
            .execute()

        if not response.data:
            return jsonify({'error': 'Payment not found'}), 404

        payment = response.data[0]
        status = payment.get('status')

        return jsonify({
            'payment_id': payment_id,
            'status': status,
            'amount': payment.get('amount'),
            'service_type': payment.get('service_type'),
            'phone': payment.get('phone'),
            'transaction_id': payment.get('transaction_id'),
            'mpesa_receipt': payment.get('mpesa_receipt_number'),
            'result_code': payment.get('mpesa_result_code'),
            'result_desc': payment.get('mpesa_result_desc'),
            'checkout_request_id': payment.get('checkout_request_id'),
            'completed_at': payment.get('completed_at'),
            'reference': payment.get('reference')
        }), 200

    except Exception as e:
        logger.error(f"❌ Error getting payment status: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── =========================================================───
# ─── ROUTE: FORCE COMPLETE PAYMENT ─────────────────────────────
# ─── =========================================================───

@mpesa_bp.route('/force-complete/<payment_id>', methods=['POST'])
def force_complete_payment(payment_id):
    """Force complete a payment manually."""
    try:
        data = request.get_json() or {}
        transaction_id = data.get('transaction_id')
        
        if not transaction_id:
            return jsonify({'success': False, 'message': 'Transaction ID is required'}), 400
        
        supabase = get_supabase()
        
        response = supabase.table('payments')\
            .select('*')\
            .eq('id', payment_id)\
            .execute()
        
        if not response.data:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404
        
        payment = response.data[0]
        
        if payment.get('status') == 'completed':
            return jsonify({
                'success': True,
                'message': 'Payment already completed',
                'payment_id': payment_id,
                'status': 'completed'
            }), 200
        
        update_data = {
            'status': 'completed',
            'transaction_id': transaction_id,
            'mpesa_receipt_number': transaction_id,
            'mpesa_result_code': '0',
            'mpesa_result_desc': 'Manually confirmed by user',
            'completed_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        result = supabase.table('payments').update(update_data).eq('id', payment_id).execute()
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"❌ Database update error: {result.error}")
            return jsonify({'success': False, 'message': f'Database error: {result.error}'}), 500
        
        logger.info(f"✅ Payment {payment_id} manually completed with TXN: {transaction_id}")
        
        return jsonify({
            'success': True,
            'message': 'Payment completed successfully!',
            'payment_id': payment_id,
            'status': 'completed',
            'transaction_id': transaction_id
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Force complete error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


# ─── =========================================================───
# ─── ROUTE: CALLBACK ────────────────────────────────────────────
# ─── =========================================================───

@mpesa_bp.route('/callback', methods=['POST', 'GET'])
def mpesa_callback():
    """Handle M-Pesa callback from Safaricom."""
    logger.info("=" * 60)
    logger.info("📥 M-PESA CALLBACK ENDPOINT HIT")
    logger.info(f"Method: {request.method}")
    logger.info(f"Client IP: {request.remote_addr}")
    
    try:
        raw_data = request.get_data(as_text=True)
        logger.info(f"Raw data (first 500 chars): {raw_data[:500] if raw_data else 'Empty'}")
        
        data = request.get_json()
        if not data:
            data = request.form.to_dict()
            if not data:
                logger.error("❌ No data in callback")
                return jsonify({'ResultCode': 1, 'ResultDesc': 'No data'}), 400
        
        try:
            sanitized = sanitize_log_data(data)
            logger.info(f"Callback data (sanitized): {json.dumps(sanitized, indent=2)[:500]}")
        except Exception as e:
            logger.warning(f"Could not sanitize callback data: {e}")
        
        result = handle_mpesa_callback(
            callback_data=data,
            client_ip=request.remote_addr
        )
        
        logger.info(f"✅ Callback result: {result}")
        
        return jsonify({
            'ResultCode': result.get('ResultCode', 0),
            'ResultDesc': result.get('ResultDesc', 'Success')
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Callback error: {e}", exc_info=True)
        return jsonify({'ResultCode': 1, 'ResultDesc': str(e)}), 200


# ─── =========================================================───
# ─── ROUTE: HEALTH CHECK ────────────────────────────────────────
# ─── =========================================================───

@mpesa_bp.route('/health', methods=['GET'])
def mpesa_health():
    """M-Pesa specific health check."""
    try:
        return jsonify({
            'status': 'healthy',
            'is_configured': is_mpesa_configured(),
            'environment': os.getenv('MPESA_ENV', 'production'),
            'shortcode': os.getenv('MPESA_SHORTCODE', '4095377'),
            'callback_url': os.getenv('MPESA_CALLBACK_URL', 'not_set'),
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ─── =========================================================───
# ─── ROUTE: CONFIG STATUS ───────────────────────────────────────
# ─── =========================================================───

@mpesa_bp.route('/config-status', methods=['GET'])
def config_status():
    """Check M-Pesa configuration status."""
    try:
        result = {
            'is_configured': is_mpesa_configured(),
            'environment': os.getenv('MPESA_ENV', 'production'),
            'shortcode': os.getenv('MPESA_SHORTCODE', '4095377'),
            'shortcode_type': os.getenv('MPESA_SHORTCODE_TYPE', 'paybill'),
            'callback_url': os.getenv('MPESA_CALLBACK_URL', 'not_set'),
            'variables': {
                'MPESA_CONSUMER_KEY': '✅' if os.getenv('MPESA_CONSUMER_KEY') else '❌',
                'MPESA_CONSUMER_SECRET': '✅' if os.getenv('MPESA_CONSUMER_SECRET') else '❌',
                'MPESA_PASSKEY': '✅' if os.getenv('MPESA_PASSKEY') else '❌',
                'MPESA_SHORTCODE': '✅' if os.getenv('MPESA_SHORTCODE') else '❌',
                'MPESA_CALLBACK_URL': '✅' if os.getenv('MPESA_CALLBACK_URL') else '❌',
            }
        }

        if result['is_configured']:
            try:
                token = get_mpesa_token()
                result['token_test'] = '✅ Success'
                result['token_preview'] = token[:20] + '...' if token else None
            except Exception as e:
                result['token_test'] = f'❌ Failed: {str(e)}'

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Config status error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
