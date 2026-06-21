# api/routes/mpesa.py - FIXED VERSION

import os
import logging
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

from services.supabase_client import get_supabase
from services.mpesa import (
    initiate_stk_push,
    query_payment_status,
    is_mpesa_configured,
    get_mpesa_token,
    handle_mpesa_callback,
    sanitize_log_data,
    verify_safaricom_ip
)

logger = logging.getLogger(__name__)
mpesa_bp = Blueprint('mpesa', __name__)


@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa callback - single source of truth."""
    logger.info("📥 M-PESA CALLBACK RECEIVED")
    
    try:
        data = request.get_json()
        if not data:
            logger.error("❌ No JSON data")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'No data'}), 400

        result = handle_mpesa_callback(
            callback_data=data,
            client_ip=request.remote_addr
        )

        return jsonify({
            'ResultCode': result.get('ResultCode', 0),
            'ResultDesc': result.get('ResultDesc', 'Success')
        }), 200

    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        return jsonify({'ResultCode': 1, 'ResultDesc': str(e)}), 200


@mpesa_bp.route('/test', methods=['GET'])
def test_route():
    return jsonify({
        'status': 'ok',
        'message': 'M-Pesa blueprint is loaded!',
        'timestamp': datetime.now().isoformat()
    }), 200


@mpesa_bp.route('/config-status', methods=['GET'])
def config_status():
    """Check M-Pesa configuration status."""
    try:
        result = {
            'is_configured': is_mpesa_configured(),
            'environment': os.getenv('MPESA_ENV', 'not_set'),
            'shortcode': os.getenv('MPESA_SHORTCODE', 'not_set'),
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


@mpesa_bp.route('/initiate', methods=['POST', 'OPTIONS'])
def initiate_payment():
    """Initiate M-Pesa STK Push payment."""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        data = request.get_json()
        logger.info(f"📥 Payment initiation request received")

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

        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400

        amount_int = int(round(amount))
        if amount_int < 1:
            return jsonify({'error': 'Amount must be at least 1 KES'}), 400

        if not is_mpesa_configured():
            logger.error("❌ M-Pesa not configured")
            return jsonify({
                'error': 'M-Pesa is not configured. Please contact support.',
                'code': 'MPESA_NOT_CONFIGURED'
            }), 503

        supabase = get_supabase()

        # ─── Create payment record ──────────────────────────────
        payment_data = {
            'user_id': data.get('user_id', 'test-user-id'),
            'service_type': service,
            'purpose': purpose,
            'amount': amount_int,
            'phone': phone,
            'client_type': client_type,
            'status': 'pending',
            'reference': f'AUTO-{uuid.uuid4().hex[:8].upper()}',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        payment_response = supabase.table('payments').insert(payment_data).execute()

        if not payment_response.data:
            logger.error(f"❌ Failed to create payment record")
            return jsonify({'error': 'Failed to create payment record'}), 500

        payment = payment_response.data[0]
        payment_id = payment['id']
        logger.info(f"✅ Created payment: {payment_id[:8]}")

        # ─── Initiate STK Push ──────────────────────────────────
        try:
            mpesa_response = initiate_stk_push(
                phone=phone,
                amount=float(amount_int),
                payment_id=payment_id,
                service=service
            )

            checkout_id = mpesa_response.get('CheckoutRequestID')
            merchant_request_id = mpesa_response.get('MerchantRequestID')

            if not checkout_id:
                logger.error(f"❌ No CheckoutRequestID for payment {payment_id[:8]}")
                supabase.table('payments').update({
                    'status': 'failed',
                    'mpesa_result_desc': 'No CheckoutRequestID from M-Pesa'
                }).eq('id', payment_id).execute()
                return jsonify({
                    'error': 'Failed to initiate STK Push. Please try again.',
                    'payment_id': payment_id
                }), 400

            # ─── SINGLE UPDATE: Update payment with checkout ID ──
            update_result = supabase.table('payments').update({
                'checkout_request_id': checkout_id,
                'merchant_request_id': merchant_request_id,
                'status': 'processing',
                'updated_at': datetime.now().isoformat()
            }).eq('id', payment_id).execute()

            if hasattr(update_result, 'error') and update_result.error:
                logger.error(f"❌ Update error: {update_result.error}")

            logger.info(f"✅ STK Push sent for payment {payment_id[:8]}, CheckoutID: {checkout_id[:8]}")

            return jsonify({
                'payment_id': payment_id,
                'checkout_id': checkout_id,
                'merchant_request_id': merchant_request_id,
                'status': 'pending',
                'message': 'STK Push sent to your phone. Please confirm the transaction.'
            }), 200

        except Exception as e:
            supabase.table('payments').update({
                'status': 'failed',
                'mpesa_result_desc': str(e)
            }).eq('id', payment_id).execute()

            logger.error(f"❌ STK Push failed for payment {payment_id[:8]}: {e}")
            return jsonify({
                'error': str(e),
                'payment_id': payment_id
            }), 400

    except Exception as e:
        logger.error(f"❌ Payment initiation error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


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
        logger.info(f"📊 Payment {payment_id[:8]} status: {status}")

        # ─── If pending and has checkout_id, query M-Pesa ──────
        if status in ['pending', 'processing'] and payment.get('checkout_request_id'):
            try:
                checkout_id = payment['checkout_request_id']
                logger.info(f"🔍 Querying M-Pesa for: {checkout_id[:8]}")

                mpesa_status = query_payment_status(checkout_id)
                result_code = mpesa_status.get('ResultCode')
                result_desc = mpesa_status.get('ResultDesc')
                transaction_id = mpesa_status.get('TransactionID')

                logger.info(f"📥 M-Pesa query result: {result_code}")

                if str(result_code) == '0':
                    update_data = {
                        'status': 'completed',
                        'transaction_id': transaction_id,
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction completed',
                        'completed_at': datetime.now().isoformat()
                    }
                    supabase.table('payments').update(update_data).eq('id', payment_id).execute()
                    status = 'completed'
                    logger.info(f"✅ Payment {payment_id[:8]} completed!")

                elif str(result_code) in ['1037', '1032']:
                    update_data = {
                        'status': 'failed',
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction cancelled'
                    }
                    supabase.table('payments').update(update_data).eq('id', payment_id).execute()
                    status = 'failed'
                    logger.warning(f"⚠️ Payment {payment_id[:8]} cancelled")

                elif str(result_code) == '2001':
                    logger.info(f"⏳ Payment {payment_id[:8]} still pending")
                    return jsonify({
                        'payment_id': payment_id,
                        'status': 'pending',
                        'amount': payment.get('amount'),
                        'service_type': payment.get('service_type'),
                        'phone': payment.get('phone'),
                        'checkout_request_id': checkout_id,
                        'message': 'Transaction still processing'
                    }), 200

                else:
                    update_data = {
                        'status': 'failed',
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction failed'
                    }
                    supabase.table('payments').update(update_data).eq('id', payment_id).execute()
                    status = 'failed'
                    logger.warning(f"❌ Payment {payment_id[:8]} failed")

            except Exception as e:
                logger.warning(f"⚠️ Failed to query M-Pesa status: {e}")

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
            'completed_at': payment.get('completed_at')
        }), 200

    except Exception as e:
        logger.error(f"❌ Error getting payment status: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
