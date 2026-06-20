# api/routes/mpesa.py – M-Pesa Routes (FULLY UPDATED)

import os
import logging
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from services.mpesa import initiate_stk_push, query_payment_status, is_mpesa_configured, get_mpesa_token
from api.auth_middleware import require_auth

logger = logging.getLogger(__name__)
mpesa_bp = Blueprint('mpesa', __name__)


# ─── Config Status ──────────────────────────────────────────────
@mpesa_bp.route('/config-status', methods=['GET'])
def config_status():
    """Check M-Pesa configuration status."""
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


# ─── Initiate Payment ────────────────────────────────────────
@mpesa_bp.route('/initiate', methods=['POST'])
@require_auth
def initiate_payment(user):
    """
    Initiate M-Pesa STK Push payment.
    Creates payment record in Supabase, then sends STK Push.
    """
    try:
        data = request.get_json()
        logger.info(f"📥 Payment initiation request from user {user.id}")
        
        # Validate required fields
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
        
        # Check M-Pesa configuration
        if not is_mpesa_configured():
            logger.error("❌ M-Pesa not configured")
            return jsonify({
                'error': 'M-Pesa is not configured. Please contact support.',
                'code': 'MPESA_NOT_CONFIGURED'
            }), 503
        
        supabase = get_supabase()
        
        # ─── Create payment record in Supabase ────────────────
        payment_data = {
            'user_id': user.id,
            'service_type': service,
            'purpose': purpose,
            'amount': amount,
            'phone': phone,
            'client_type': client_type,
            'status': 'pending',
            'reference': f'AUTO-{uuid.uuid4().hex[:8].upper()}',
            'created_at': datetime.now().isoformat()
        }
        
        payment_response = supabase.table('payments').insert(payment_data).execute()
        
        if not payment_response.data:
            logger.error(f"❌ Failed to create payment record for user {user.id}")
            return jsonify({'error': 'Failed to create payment record'}), 500
        
        payment = payment_response.data[0]
        payment_id = payment['id']
        
        # ─── Initiate STK Push ──────────────────────────────────
        try:
            mpesa_response = initiate_stk_push(
                phone=phone,
                amount=amount,
                payment_id=payment_id,
                service=service
            )
            
            checkout_id = mpesa_response.get('CheckoutRequestID')
            merchant_request_id = mpesa_response.get('MerchantRequestID')
            
            # ─── VALIDATE checkout_id is not None ────────────────
            if not checkout_id:
                logger.error(f"❌ No CheckoutRequestID received for payment {payment_id}")
                supabase.table('payments').update({
                    'status': 'failed',
                    'mpesa_result_desc': 'No CheckoutRequestID from M-Pesa'
                }).eq('id', payment_id).execute()
                return jsonify({
                    'error': 'Failed to initiate STK Push. Please try again.',
                    'payment_id': payment_id
                }), 400
            
            # Update payment with checkout ID
            update_result = supabase.table('payments').update({
                'checkout_request_id': checkout_id,
                'merchant_request_id': merchant_request_id
            }).eq('id', payment_id).execute()
            
            if not update_result.data:
                logger.error(f"❌ Failed to update payment with checkout_id: {payment_id}")
            
            logger.info(f"✅ STK Push sent for payment {payment_id}, CheckoutID: {checkout_id}")
            
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
            
            logger.error(f"❌ STK Push failed for payment {payment_id}: {e}")
            return jsonify({
                'error': str(e),
                'payment_id': payment_id
            }), 400
        
    except ValueError as e:
        return jsonify({'error': f'Invalid amount: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"❌ Payment initiation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ─── Get Payment Status ──────────────────────────────────────
@mpesa_bp.route('/status/<payment_id>', methods=['GET'])
@require_auth
def get_payment_status(user, payment_id):
    """
    Get the current status of a payment from Supabase and query M-Pesa if pending.
    """
    try:
        supabase = get_supabase()
        
        response = supabase.table('payments')\
            .select('*')\
            .eq('id', payment_id)\
            .eq('user_id', user.id)\
            .execute()
        
        if not response.data:
            return jsonify({'error': 'Payment not found'}), 404
        
        payment = response.data[0]
        logger.info(f"📊 Payment status check: {payment_id} - current status: {payment.get('status')}")
        
        # ─── Query M-Pesa if still pending ──────────────────────
        if payment['status'] == 'pending' and payment.get('checkout_request_id'):
            try:
                checkout_id = payment['checkout_request_id']
                logger.info(f"🔍 Querying M-Pesa for checkout: {checkout_id}")
                
                mpesa_status = query_payment_status(checkout_id)
                logger.info(f"📥 M-Pesa query response: {mpesa_status}")
                
                result_code = mpesa_status.get('ResultCode')
                result_desc = mpesa_status.get('ResultDesc')
                transaction_id = mpesa_status.get('TransactionID')
                
                # ─── Update payment based on M-Pesa response ──────────
                if str(result_code) == '0':
                    # ✅ Payment completed
                    new_status = 'completed'
                    update_data = {
                        'status': new_status,
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction completed',
                        'transaction_id': transaction_id,
                        'completed_at': datetime.now().isoformat()
                    }
                    logger.info(f"✅ Payment {payment_id} completed! Transaction ID: {transaction_id}")
                    
                elif str(result_code) in ['1037', '1032']:
                    # ❌ User cancelled or failed
                    new_status = 'failed'
                    update_data = {
                        'status': new_status,
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction cancelled or failed'
                    }
                    logger.warning(f"⚠️ Payment {payment_id} failed/cancelled: {result_desc}")
                    
                elif str(result_code) == '2001':
                    # ⏳ Transaction still pending at M-Pesa
                    logger.info(f"⏳ Payment {payment_id} still pending at M-Pesa")
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
                    # ❌ Transaction failed
                    new_status = 'failed'
                    update_data = {
                        'status': new_status,
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction failed'
                    }
                    logger.warning(f"❌ Payment {payment_id} failed: {result_desc} (Code: {result_code})")
                
                # ─── Update Supabase if status changed ──────────────────
                if new_status != payment['status']:
                    result = supabase.table('payments').update(update_data).eq('id', payment_id).execute()
                    if result.data:
                        payment.update(update_data)
                        logger.info(f"📝 Payment {payment_id} updated to: {new_status}")
                    else:
                        logger.error(f"❌ Failed to update payment {payment_id}")
                
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
        
        # ─── Return payment status ──────────────────────────────
        return jsonify({
            'payment_id': payment_id,
            'status': payment.get('status'),
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


# ─── M-Pesa Callback ─────────────────────────────────────────
@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """
    Handle M-Pesa callback from Safaricom.
    Properly parses the callback structure.
    """
    try:
        # ─── Log raw request ──────────────────────────────────────
        raw_data = request.get_data(as_text=True)
        logger.info("=" * 60)
        logger.info("📥 M-PESA CALLBACK RECEIVED")
        
        # ─── Parse JSON ────────────────────────────────────────────
        data = request.get_json()
        if not data:
            logger.error("❌ No JSON data in callback")
            logger.info(f"Raw data: {raw_data[:200]}")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'No data'}), 400
        
        logger.info(f"Full callback: {json.dumps(data, indent=2)}")
        
        # ─── Extract callback data ──────────────────────────────
        stk_callback = data.get('Body', {}).get('stkCallback', {})
        
        if not stk_callback:
            logger.error("❌ No stkCallback found")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Invalid structure'}), 400
        
        checkout_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        
        logger.info(f"📊 CheckoutID: {checkout_id}")
        logger.info(f"📊 ResultCode: {result_code}")
        logger.info(f"📊 ResultDesc: {result_desc}")
        
        if not checkout_id:
            logger.error("❌ No CheckoutRequestID")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Missing CheckoutRequestID'}), 400
        
        # ─── Extract transaction details ─────────────────────────
        transaction_id = None
        mpesa_receipt = None
        amount = None
        phone = None
        
        callback_metadata = stk_callback.get('CallbackMetadata')
        if callback_metadata:
            logger.info(f"📋 Metadata: {callback_metadata}")
            items = callback_metadata.get('Item', [])
            for item in items:
                name = item.get('Name')
                value = item.get('Value')
                logger.info(f"  {name}: {value}")
                
                # ✅ CORRECT M-Pesa field name
                if name == 'MpesaReceiptNumber':
                    mpesa_receipt = value
                    transaction_id = value
                elif name == 'Amount':
                    amount = value
                elif name == 'PhoneNumber':
                    phone = value
                elif name == 'TransactionID' and not mpesa_receipt:
                    mpesa_receipt = value
                    transaction_id = value
        else:
            logger.warning("⚠️ No CallbackMetadata found")
        
        logger.info(f"💰 Receipt: {mpesa_receipt}")
        logger.info(f"💰 Amount: {amount}")
        logger.info(f"📱 Phone: {phone}")
        
        # ─── Update database ──────────────────────────────────────
        supabase = get_supabase()
        
        # Primary: Find by checkout_request_id
        response = supabase.table('payments')\
            .select('*')\
            .eq('checkout_request_id', checkout_id)\
            .execute()
        
        # Fallback: Try to find by transaction_id
        if not response.data and transaction_id:
            logger.info(f"🔍 Trying transaction_id: {transaction_id}")
            response = supabase.table('payments')\
                .select('*')\
                .eq('transaction_id', transaction_id)\
                .execute()
        
        if not response.data:
            logger.error(f"❌ Payment not found for CheckoutID: {checkout_id}")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Payment not found'}), 404
        
        payment = response.data[0]
        payment_id = payment['id']
        logger.info(f"✅ Found payment: {payment_id}")
        
        # ─── Idempotency check ─────────────────────────────────────
        if payment.get('status') == 'completed':
            logger.info(f"ℹ️ Payment {payment_id} already completed. Skipping duplicate.")
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
        
        # ─── Update status ────────────────────────────────────────
        if str(result_code) == '0':
            update_data = {
                'status': 'completed',
                'mpesa_result_code': str(result_code),
                'mpesa_result_desc': result_desc or 'Transaction completed',
                'transaction_id': transaction_id,
                'mpesa_receipt_number': mpesa_receipt,
                'amount_paid': amount,
                'completed_at': datetime.now().isoformat()
            }
            logger.info(f"✅ Updating payment {payment_id} to COMPLETED")
            
        elif str(result_code) in ['1037', '1032']:
            update_data = {
                'status': 'failed',
                'mpesa_result_code': str(result_code),
                'mpesa_result_desc': result_desc or 'Transaction cancelled'
            }
            logger.warning(f"⚠️ Payment {payment_id} CANCELLED")
            
        else:
            update_data = {
                'status': 'failed',
                'mpesa_result_code': str(result_code),
                'mpesa_result_desc': result_desc or f'Failed with code {result_code}'
            }
            logger.warning(f"❌ Payment {payment_id} FAILED")
        
        # ─── Execute update ──────────────────────────────────────
        result = supabase.table('payments').update(update_data).eq('id', payment_id).execute()
        
        if result.data:
            logger.info(f"✅ Database updated successfully: {result.data[0].get('status')}")
        else:
            logger.error("❌ Database update failed")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Update failed'}), 500
        
        logger.info("=" * 60)
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
        
    except Exception as e:
        logger.error(f"❌ Callback error: {e}", exc_info=True)
        return jsonify({'ResultCode': 1, 'ResultDesc': str(e)}), 500


# ─── Debug: Force Complete Payment ──────────────────────────
@mpesa_bp.route('/force-complete/<payment_id>', methods=['POST'])
@require_auth
def force_complete_payment(user, payment_id):
    """
    Force complete a payment (admin only).
    """
    try:
        supabase = get_supabase()
        
        # Check if user is admin
        profile = supabase.table('user_profiles').select('role').eq('id', user.id).execute()
        if not profile.data or profile.data[0].get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        result = supabase.table('payments').update({
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        }).eq('id', payment_id).execute()
        
        if result.data:
            logger.info(f"✅ Force completed payment {payment_id}")
            return jsonify({'success': True, 'payment': result.data[0]}), 200
        return jsonify({'error': 'Payment not found'}), 404
    except Exception as e:
        logger.error(f"❌ Force complete error: {e}")
        return jsonify({'error': str(e)}), 500


# ─── Debug: Callback Tester ─────────────────────────────────
@mpesa_bp.route('/callback-debug', methods=['GET', 'POST'])
def mpesa_callback_debug():
    """
    Debug endpoint to see what M-Pesa is sending.
    """
    if request.method == 'POST':
        data = request.get_json()
        logger.info("=" * 60)
        logger.info("🔍 CALLBACK DEBUG - FULL PAYLOAD:")
        logger.info(json.dumps(data, indent=2) if data else "No data")
        logger.info("=" * 60)
        
        # Log headers
        logger.info("📋 Headers:")
        for key, value in request.headers.items():
            logger.info(f"  {key}: {value}")
        
        # Try to extract checkout_id
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
    
    return jsonify({
        'message': 'Send POST to this endpoint for debugging',
        'usage': 'curl -X POST https://auto-v.onrender.com/api/mpesa/callback-debug -H "Content-Type: application/json" -d \'{"test":"data"}\''
    }), 200
