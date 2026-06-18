# api/routes/mpesa.py – M-Pesa Routes

import logging
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from services.mpesa import initiate_stk_push, query_payment_status, is_mpesa_configured
from api.auth_middleware import require_auth

logger = logging.getLogger(__name__)
mpesa_bp = Blueprint('mpesa', __name__)

# ─── Initiate Payment ────────────────────────────────────────
@mpesa_bp.route('/initiate', methods=['POST'])
@require_auth
def initiate_payment(user):
    """
    Initiate M-Pesa STK Push payment.
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['phone', 'amount', 'service', 'purpose']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        phone = data.get('phone')
        amount = float(data.get('amount'))
        service = data.get('service')
        purpose = data.get('purpose')
        
        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400
        
        # Check M-Pesa configuration
        if not is_mpesa_configured():
            logger.error("M-Pesa not configured")
            return jsonify({
                'error': 'M-Pesa is not configured. Please contact support.'
            }), 503
        
        # Create payment record
        supabase = get_supabase()
        payment_data = {
            'user_id': user.id,
            'service_type': service,
            'purpose': purpose,
            'amount': amount,
            'payment_method': 'mpesa',
            'status': 'pending',
            'mpesa_phone': phone,
            'reference': f'AUTO-{uuid.uuid4().hex[:8].upper()}',
            'created_at': datetime.now().isoformat()
        }
        
        payment_response = supabase.table('payments').insert(payment_data).execute()
        
        if not payment_response.data:
            logger.error(f"Failed to create payment record for user {user.id}")
            return jsonify({'error': 'Failed to create payment record'}), 500
        
        payment = payment_response.data[0]
        payment_id = payment['id']
        
        # Initiate STK Push
        try:
            mpesa_response = initiate_stk_push(
                phone=phone,
                amount=amount,
                payment_id=payment_id,
                service=service
            )
            
            checkout_id = mpesa_response.get('CheckoutRequestID')
            if checkout_id:
                supabase.table('payments').update({
                    'mpesa_checkout_id': checkout_id
                }).eq('id', payment_id).execute()
            
            return jsonify({
                'payment_id': payment_id,
                'checkout_id': checkout_id,
                'status': 'pending',
                'message': 'STK Push sent to your phone. Please confirm the transaction.'
            }), 200
            
        except Exception as e:
            supabase.table('payments').update({
                'status': 'failed',
                'mpesa_result_desc': str(e)
            }).eq('id', payment_id).execute()
            
            logger.error(f"STK Push failed for payment {payment_id}: {e}")
            return jsonify({
                'error': str(e),
                'payment_id': payment_id
            }), 400
        
    except ValueError as e:
        return jsonify({'error': f'Invalid amount: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Payment initiation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ─── Get Payment Status ──────────────────────────────────────
@mpesa_bp.route('/status/<payment_id>', methods=['GET'])
@require_auth
def get_payment_status(payment_id):
    """Get the current status of a payment."""
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
        
        # If payment is still pending, query M-Pesa
        if payment['status'] == 'pending' and payment.get('mpesa_checkout_id'):
            try:
                checkout_id = payment['mpesa_checkout_id']
                mpesa_status = query_payment_status(checkout_id)
                
                result_code = mpesa_status.get('ResultCode')
                result_desc = mpesa_status.get('ResultDesc')
                
                if result_code == '0':
                    new_status = 'completed'
                elif result_code == '1037':
                    new_status = 'failed'  # User cancelled
                else:
                    new_status = 'failed'
                
                if new_status != payment['status']:
                    update_data = {
                        'status': new_status,
                        'mpesa_result_code': result_code,
                        'mpesa_result_desc': result_desc
                    }
                    if new_status == 'completed':
                        update_data['transaction_id'] = mpesa_status.get('TransactionID')
                        update_data['completed_at'] = datetime.now().isoformat()
                    
                    supabase.table('payments').update(update_data).eq('id', payment_id).execute()
                    payment['status'] = new_status
                    
            except Exception as e:
                logger.warning(f"Failed to query payment status: {e}")
        
        return jsonify({
            'payment_id': payment_id,
            'status': payment.get('status'),
            'amount': payment.get('amount'),
            'service_type': payment.get('service_type'),
            'mpesa_phone': payment.get('mpesa_phone'),
            'transaction_id': payment.get('transaction_id'),
            'result_code': payment.get('mpesa_result_code'),
            'result_desc': payment.get('mpesa_result_desc')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ─── M-Pesa Callback ─────────────────────────────────────────
@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """
    Handle M-Pesa callback from Safaricom.
    """
    try:
        data = request.get_json()
        logger.info(f"📥 M-Pesa callback received: {data}")
        
        stk_callback = data.get('Body', {}).get('stkCallback', {})
        
        if not stk_callback:
            logger.error("Invalid callback structure: missing stkCallback")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Invalid callback structure'}), 400
        
        checkout_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        transaction_id = stk_callback.get('TransactionID')
        
        logger.info(f"Callback: CheckoutID={checkout_id}, ResultCode={result_code}, ResultDesc={result_desc}")
        
        if not checkout_id:
            logger.error("Callback missing CheckoutRequestID")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Missing CheckoutRequestID'}), 400
        
        supabase = get_supabase()
        response = supabase.table('payments')\
            .select('*')\
            .eq('mpesa_checkout_id', checkout_id)\
            .execute()
        
        if not response.data:
            logger.error(f"Payment not found for CheckoutRequestID: {checkout_id}")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Payment not found'}), 404
        
        payment = response.data[0]
        payment_id = payment['id']
        
        # Idempotency check
        if payment.get('status') == 'completed':
            logger.info(f"Payment {payment_id} already completed. Skipping duplicate callback.")
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
        
        # Update payment status
        if result_code == '0':
            new_status = 'completed'
            update_data = {
                'status': new_status,
                'mpesa_result_code': result_code,
                'mpesa_result_desc': result_desc,
                'transaction_id': transaction_id,
                'completed_at': datetime.now().isoformat()
            }
            logger.info(f"✅ Payment {payment_id} completed successfully. Transaction ID: {transaction_id}")
        else:
            new_status = 'failed'
            update_data = {
                'status': new_status,
                'mpesa_result_code': result_code,
                'mpesa_result_desc': result_desc
            }
            logger.warning(f"❌ Payment {payment_id} failed: {result_desc}")
        
        supabase.table('payments').update(update_data).eq('id', payment_id).execute()
        
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
        
    except Exception as e:
        logger.error(f"Error processing callback: {e}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Internal server error'}), 500
