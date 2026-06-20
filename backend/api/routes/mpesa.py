# api/routes/mpesa.py – M-Pesa Routes (FIXED)

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
            
            # ─── Validate checkout_id is not None ──────────────
            if not checkout_id:
                logger.error(f"❌ No CheckoutRequestID received for payment {payment_id}")
                # Update payment as failed
                supabase.table('payments').update({
                    'status': 'failed',
                    'mpesa_result_desc': 'No CheckoutRequestID received from M-Pesa'
                }).eq('id', payment_id).execute()
                return jsonify({
                    'error': 'Failed to initiate STK Push. Please try again.',
                    'payment_id': payment_id
                }), 400
            
            # Update payment with checkout ID
            supabase.table('payments').update({
                'checkout_request_id': checkout_id,
                'merchant_request_id': merchant_request_id
            }).eq('id', payment_id).execute()
            
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
    Get the current status of a payment.
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
        logger.info(f"📊 Payment {payment_id} status: {payment.get('status')}")
        
        # ─── If pending and has checkout_id, query M-Pesa ──────
        if payment['status'] == 'pending' and payment.get('checkout_request_id'):
            try:
                checkout_id = payment['checkout_request_id']
                logger.info(f"🔍 Querying M-Pesa for: {checkout_id}")
                
                mpesa_status = query_payment_status(checkout_id)
                result_code = mpesa_status.get('ResultCode')
                result_desc = mpesa_status.get('ResultDesc')
                transaction_id = mpesa_status.get('TransactionID')
                
                logger.info(f"📥 M-Pesa result: Code={result_code}, Desc={result_desc}")
                
                if str(result_code) == '0':
                    # ✅ Payment completed
                    update_data = {
                        'status': 'completed',
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction completed',
                        'transaction_id': transaction_id,
                        'completed_at': datetime.now().isoformat()
                    }
                    result = supabase.table('payments').update(update_data).eq('id', payment_id).execute()
                    if result.data:
                        payment.update(update_data)
                        logger.info(f"✅ Payment {payment_id} completed! TXN: {transaction_id}")
                    else:
                        logger.error(f"❌ Failed to update payment {payment_id}")
                    
                elif str(result_code) in ['1037', '1032']:
                    # ❌ User cancelled or failed
                    update_data = {
                        'status': 'failed',
                        'mpesa_result_code': str(result_code),
                        'mpesa_result_desc': result_desc or 'Transaction failed'
                    }
                    result = supabase.table('payments').update(update_data).eq('id', payment_id).execute()
                    if result.data:
                        payment.update(update_data)
                        logger.warning(f"❌ Payment {payment_id} failed: {result_desc}")
                    
                elif str(result_code) == '2001':
                    # ⏳ Still pending
                    logger.info(f"⏳ Payment {payment_id} still pending")
                    return jsonify({
                        'payment_id': payment_id,
                        'status': 'pending',
                        'amount': payment.get('amount'),
                        'service_type': payment.get('service_type'),
                        'phone': payment.get('phone'),
                        'checkout_request_id': checkout_id,
                        'message': 'Transaction still processing'
                    }), 200
                    
            except Exception as e:
                logger.warning(f"⚠️ M-Pesa query failed: {e}")
                return jsonify({
                    'payment_id': payment_id,
                    'status': 'pending',
                    'amount': payment.get('amount'),
                    'service_type': payment.get('service_type'),
                    'phone': payment.get('phone'),
                    'message': 'Unable to verify status'
                }), 200
        
        # ─── Return current status ──────────────────────────────
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
        logger.error(f"❌ Status error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── M-Pesa Callback ─────────────────────────────────────────
@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """
    Handle M-Pesa callback from Safaricom.
    Properly parses the callback structure.
    """
    try:
        data = request.get_json()
        logger.info(f"📥 M-Pesa callback received")
        
        # ─── Step 1: Validate callback structure ──────────────────
        if not data:
            logger.error("❌ No data in callback")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'No data'}), 400
        
        # Validate Body exists
        if 'Body' not in data:
            logger.error("❌ Missing Body in callback")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Missing Body'}), 400
        
        body = data.get('Body', {})
        
        # Validate stkCallback exists
        if 'stkCallback' not in body:
            logger.error("❌ Missing stkCallback in Body")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Missing stkCallback'}), 400
        
        stk_callback = body.get('stkCallback', {})
        
        # ─── Step 2: Extract required fields ──────────────────────
        checkout_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        
        logger.info(f"📦 Callback: CheckoutID={checkout_id}, ResultCode={result_code}")
        
        # Validate CheckoutRequestID
        if not checkout_id:
            logger.error("❌ Callback missing CheckoutRequestID")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Missing CheckoutRequestID'}), 400
        
        # ─── Step 3: Extract transaction details from metadata ────
        transaction_id = None
        mpesa_receipt = None
        amount = None
        phone = None
        
        callback_metadata = stk_callback.get('CallbackMetadata')
        if callback_metadata and isinstance(callback_metadata, dict):
            items = callback_metadata.get('Item', [])
            if items and isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    name = item.get('Name')
                    value = item.get('Value')
                    
                    # ✅ CORRECT M-Pesa field name
                    if name == 'MpesaReceiptNumber':
                        mpesa_receipt = value
                        transaction_id = value
                        logger.info(f"✅ Found MpesaReceiptNumber: {value}")
                    elif name == 'Amount':
                        amount = value
                        logger.info(f"💰 Amount: {value}")
                    elif name == 'PhoneNumber':
                        phone = value
                        logger.info(f"📱 Phone: {value}")
                    elif name == 'TransactionID':
                        # Fallback if MpesaReceiptNumber not found
                        if not mpesa_receipt:
                            mpesa_receipt = value
                            transaction_id = value
                            logger.info(f"✅ Found TransactionID: {value}")
        else:
            logger.warning("⚠️ No CallbackMetadata found")
        
        # ─── Step 4: Log callback details ──────────────────────────
        logger.info(f"📊 Callback details:")
        logger.info(f"   CheckoutID: {checkout_id}")
        logger.info(f"   ResultCode: {result_code}")
        logger.info(f"   ResultDesc: {result_desc}")
        logger.info(f"   TransactionID: {transaction_id}")
        logger.info(f"   MpesaReceipt: {mpesa_receipt}")
        logger.info(f"   Amount: {amount}")
        logger.info(f"   Phone: {phone}")
        
        # ─── Step 5: Find and update payment ──────────────────────
        supabase = get_supabase()
        
        # Try to find by checkout_request_id (primary)
        response = supabase.table('payments')\
            .select('*')\
            .eq('checkout_request_id', checkout_id)\
            .execute()
        
        if not response.data:
            # Fallback: try to find by reference or other means
            logger.warning(f"⚠️ No payment found for CheckoutID: {checkout_id}")
            
            # Check if we can find by transaction_id (if we have it)
            if transaction_id:
                response = supabase.table('payments')\
                    .select('*')\
                    .eq('transaction_id', transaction_id)\
                    .execute()
                
                if response.data:
                    logger.info(f"✅ Found payment by transaction_id: {transaction_id}")
            
            # If still not found, return error
            if not response.data:
                logger.error(f"❌ Payment not found for CheckoutID: {checkout_id}")
                return jsonify({'ResultCode': 1, 'ResultDesc': 'Payment not found'}), 404
        
        payment = response.data[0]
        payment_id = payment['id']
        logger.info(f"📝 Found payment: {payment_id}")
        
        # ─── Step 6: Idempotency check ─────────────────────────────
        if payment.get('status') == 'completed':
            logger.info(f"ℹ️ Payment {payment_id} already completed. Skipping duplicate.")
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
        
        # ─── Step 7: Update payment status ─────────────────────────
        if str(result_code) == '0':
            new_status = 'completed'
            update_data = {
                'status': new_status,
                'mpesa_result_code': str(result_code),
                'mpesa_result_desc': result_desc or 'Transaction completed successfully',
                'transaction_id': transaction_id,
                'mpesa_receipt_number': mpesa_receipt,
                'amount_paid': amount,
                'completed_at': datetime.now().isoformat()
            }
            logger.info(f"✅ Payment {payment_id} completed. Receipt: {mpesa_receipt}")
            
        elif str(result_code) in ['1037']:
            new_status = 'failed'
            update_data = {
                'status': new_status,
                'mpesa_result_code': str(result_code),
                'mpesa_result_desc': result_desc or 'User cancelled transaction'
            }
            logger.warning(f"⚠️ Payment {payment_id} cancelled by user")
            
        else:
            new_status = 'failed'
            update_data = {
                'status': new_status,
                'mpesa_result_code': str(result_code),
                'mpesa_result_desc': result_desc or f'Transaction failed with code {result_code}'
            }
            logger.warning(f"❌ Payment {payment_id} failed: {result_desc} (Code: {result_code})")
        
        # ─── Step 8: Update Supabase with error handling ───────────
        try:
            result = supabase.table('payments').update(update_data).eq('id', payment_id).execute()
            
            if not result.data:
                logger.error(f"❌ Failed to update payment {payment_id}")
                return jsonify({'ResultCode': 1, 'ResultDesc': 'Update failed'}), 500
            
            logger.info(f"📝 Payment {payment_id} updated to: {new_status}")
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
            
        except Exception as db_error:
            logger.error(f"❌ Database update error: {db_error}")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Database error'}), 500
        
    except Exception as e:
        logger.error(f"❌ Error processing callback: {e}", exc_info=True)
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Internal server error'}), 500
