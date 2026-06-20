# api/routes/mpesa.py - COMPLETE FIXED FILE

import os
import logging
import uuid
import json
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, current_app

# ─── Import from services ──────────────────────────────────────
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

# ─── CREATE BLUEPRINT ──────────────────────────────────────────
mpesa_bp = Blueprint('mpesa', __name__)


# ─── SIMPLE TEST ROUTE ─────────────────────────────────────────
@mpesa_bp.route('/test', methods=['GET'])
def test_route():
    """Simple test to verify blueprint is loaded."""
    return jsonify({
        'status': 'ok',
        'message': 'M-Pesa blueprint is loaded!',
        'timestamp': datetime.now().isoformat()
    }), 200


# ─── CONFIG STATUS ──────────────────────────────────────────────
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


# ─── INITIATE PAYMENT ────────────────────────────────────────
@mpesa_bp.route('/initiate', methods=['POST', 'OPTIONS'])
def initiate_payment():
    """
    Initiate M-Pesa STK Push payment.
    Note: Authentication is bypassed for testing.
    """
    # ─── Handle OPTIONS preflight ───────────────────────────────
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

        # ─── Check M-Pesa configuration ──────────────────────────
        if not is_mpesa_configured():
            logger.error("❌ M-Pesa not configured")
            return jsonify({
                'error': 'M-Pesa is not configured. Please contact support.',
                'code': 'MPESA_NOT_CONFIGURED'
            }), 503

        # ─── Get Supabase client ──────────────────────────────────
        supabase = get_supabase()

        # ─── Create payment record ──────────────────────────────
        payment_data = {
            'user_id': 'test-user-id',  # Temporary for testing
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

            # ─── Update payment with checkout ID ──────────────────
            update_result = supabase.table('payments').update({
                'checkout_request_id': checkout_id,
                'merchant_request_id': merchant_request_id,
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
            # Update payment as failed
            supabase.table('payments').update({
                'status': 'failed',
                'mpesa_result_desc': str(e)
            }).eq('id', payment_id).execute()

            logger.error(f"❌ STK Push failed for payment {payment_id[:8]}: {e}")
            return jsonify({
                'error': str(e),
                'payment_id': payment_id
            }), 400

    except ValueError as e:
        return jsonify({'error': f'Invalid amount: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"❌ Payment initiation error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── GET PAYMENT STATUS ──────────────────────────────────────
@mpesa_bp.route('/status/<payment_id>', methods=['GET', 'OPTIONS'])
def get_payment_status(payment_id):
    """
    Get the current status of a payment from Supabase.
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        supabase = get_supabase()

        response = supabase.table('payments')\
            .select('*')\
            .eq('id', payment_id)\
            .execute()

        if hasattr(response, 'error') and response.error:
            logger.error(f"❌ DB error: {response.error}")
            return jsonify({'error': 'Database error'}), 500

        if not response.data:
            return jsonify({'error': 'Payment not found'}), 404

        payment = response.data[0]
        status = payment.get('status')
        logger.info(f"📊 Payment {payment_id[:8]} status: {status}")

        # ─── If pending and has checkout_id, query M-Pesa ──────
        if status == 'pending' and payment.get('checkout_request_id'):
            try:
                checkout_id = payment['checkout_request_id']
                logger.info(f"🔍 Querying M-Pesa for: {checkout_id[:8]}")

                mpesa_status = query_payment_status(checkout_id)
                result_code = mpesa_status.get('ResultCode')
                result_desc = mpesa_status.get('ResultDesc')
                transaction_id = mpesa_status.get('TransactionID')

                logger.info(f"📥 M-Pesa query result: {result_code}")

                if str(result_code) == '0':
                    # ✅ Payment completed
                    update_data = {
                        'status': 'completed',
                        'transaction_id': transaction_id,
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction completed',
                        'completed_at': datetime.now().isoformat()
                    }
                    supabase.table('payments').update(update_data).eq('id', payment_id).execute()
                    status = 'completed'
                    logger.info(f"✅ Payment {payment_id[:8]} completed! TXN: {transaction_id[:8] if transaction_id else 'N/A'}")

                elif str(result_code) in ['1037', '1032']:
                    # ❌ User cancelled
                    update_data = {
                        'status': 'failed',
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction cancelled'
                    }
                    supabase.table('payments').update(update_data).eq('id', payment_id).execute()
                    status = 'failed'
                    logger.warning(f"⚠️ Payment {payment_id[:8]} cancelled: {result_desc}")

                elif str(result_code) == '2001':
                    # ⏳ Still pending
                    logger.info(f"⏳ Payment {payment_id[:8]} still pending at M-Pesa")
                    return jsonify({
                        'payment_id': payment_id,
                        'status': 'pending',
                        'amount': payment.get('amount'),
                        'service_type': payment.get('service_type'),
                        'phone': payment.get('phone'),
                        'checkout_request_id': checkout_id,
                        'message': 'Transaction still processing at M-Pesa'
                    }), 200

                else:
                    # ❌ Failed
                    update_data = {
                        'status': 'failed',
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction failed'
                    }
                    supabase.table('payments').update(update_data).eq('id', payment_id).execute()
                    status = 'failed'
                    logger.warning(f"❌ Payment {payment_id[:8]} failed: {result_desc}")

            except Exception as e:
                logger.warning(f"⚠️ Failed to query M-Pesa status: {e}")
                return jsonify({
                    'payment_id': payment_id,
                    'status': 'pending',
                    'amount': payment.get('amount'),
                    'service_type': payment.get('service_type'),
                    'phone': payment.get('phone'),
                    'checkout_request_id': payment.get('checkout_request_id'),
                    'message': 'Unable to verify status with M-Pesa'
                }), 200

        # ─── Return current status ──────────────────────────────
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


# ─── M-PESA CALLBACK ──────────────────────────────────────────
@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """
    Handle M-Pesa callback from Safaricom.
    """
    try:
        raw_data = request.get_data(as_text=True)
        logger.info("=" * 60)
        logger.info("📥 M-PESA CALLBACK RECEIVED")
        logger.info(f"Raw data length: {len(raw_data)}")
        logger.info(f"Client IP: {request.remote_addr}")

        data = request.get_json()
        if not data:
            logger.error("❌ No JSON data in callback")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'No data'}), 400

        # Sanitize before logging
        try:
            sanitized = sanitize_log_data(data)
            logger.info(f"Callback data (sanitized): {json.dumps(sanitized, indent=2)[:500]}")
        except Exception as e:
            logger.warning(f"Could not sanitize callback data: {e}")

        # Use the hardened callback handler
        result = handle_mpesa_callback(
            callback_data=data,
            client_ip=request.remote_addr
        )

        if result.get('ResultCode') == 0:
            logger.info(f"✅ Callback processed successfully")
        else:
            logger.warning(f"⚠️ Callback processing failed: {result.get('ResultDesc')}")

        return jsonify({
            'ResultCode': result.get('ResultCode', 0),
            'ResultDesc': result.get('ResultDesc', 'Success')
        }), 200

    except Exception as e:
        logger.error(f"❌ Callback error: {e}", exc_info=True)
        return jsonify({'ResultCode': 1, 'ResultDesc': str(e)}), 200


# ─── DEBUG: CALLBACK TESTER ──────────────────────────────────
@mpesa_bp.route('/callback-debug', methods=['GET', 'POST'])
def mpesa_callback_debug():
    """
    Debug endpoint to see what M-Pesa is sending.
    """
    if request.method == 'POST':
        try:
            data = request.get_json()
            logger.info("=" * 60)
            logger.info("🔍 CALLBACK DEBUG - FULL PAYLOAD:")

            if data:
                try:
                    sanitized = sanitize_log_data(data)
                    logger.info(json.dumps(sanitized, indent=2))
                except:
                    logger.info(str(data)[:1000])
            else:
                logger.info("No data")

            logger.info("=" * 60)

            checkout_id = None
            result_code = None
            if data and 'Body' in data:
                stk = data.get('Body', {}).get('stkCallback', {})
                checkout_id = stk.get('CheckoutRequestID')
                result_code = stk.get('ResultCode')
                logger.info(f"📊 Extracted: CheckoutID={checkout_id}, ResultCode={result_code}")

            return jsonify({
                'status': 'received',
                'checkout_id': checkout_id,
                'result_code': result_code,
                'message': 'Debug callback received'
            }), 200

        except Exception as e:
            logger.error(f"Debug callback error: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    return jsonify({
        'message': 'Send POST to this endpoint for debugging',
        'usage': 'curl -X POST https://auto-v.onrender.com/api/mpesa/callback-debug -H "Content-Type: application/json" -d \'{"test":"data"}\''
    }), 200
