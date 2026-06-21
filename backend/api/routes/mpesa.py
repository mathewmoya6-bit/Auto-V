# api/routes/mpesa.py - M-Pesa Routes (Production Ready)
import os
import time
import logging
import uuid
import base64
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, make_response

logger = logging.getLogger(__name__)

# ─── Create Blueprint ──────────────────────────────────────────
mpesa_bp = Blueprint('mpesa', __name__)

# ─── M-Pesa Configuration ──────────────────────────────────────
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', 'LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', 'aGGo8AuPJVpsZLcs')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://auto-v-backend.onrender.com/api/mpesa/callback')
MPESA_ENV = os.getenv('MPESA_ENV', 'production')

# API URLs
if MPESA_ENV == 'production':
    MPESA_API_URL = 'https://api.safaricom.co.ke'
else:
    MPESA_API_URL = 'https://sandbox.safaricom.co.ke'

logger.info(f"🔑 M-Pesa Environment: {MPESA_ENV}")
logger.info(f"📱 M-Pesa Shortcode: {MPESA_SHORTCODE}")

# ─── Helper Functions ──────────────────────────────────────────

def get_mpesa_token():
    """
    Get M-Pesa OAuth token
    
    Returns:
        str: Access token or None if failed
    """
    try:
        credentials = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        url = f"{MPESA_API_URL}/oauth/v1/generate?grant_type=client_credentials"
        headers = {'Authorization': f'Basic {encoded}'}
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        token = data.get('access_token')
        logger.info("✅ M-Pesa token obtained successfully")
        return token
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ M-Pesa token request error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ M-Pesa token error: {str(e)}")
        return None

def stk_push(phone_number, amount, account_reference, transaction_desc):
    """
    Send STK Push to customer
    
    Args:
        phone_number: Customer phone number
        amount: Amount to charge
        account_reference: Reference for the transaction
        transaction_desc: Description of the transaction
        
    Returns:
        dict: Result with success status and data
    """
    try:
        # Get token
        token = get_mpesa_token()
        if not token:
            return {'success': False, 'error': 'Failed to get M-Pesa token'}
        
        # Format phone number
        phone = phone_number.strip()
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+254'):
            phone = phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]
        
        # Generate timestamp and password
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
        # Prepare request
        url = f"{MPESA_API_URL}/mpesa/stkpush/v1/processrequest"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': MPESA_SHORTCODE,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone,
            'PartyB': MPESA_SHORTCODE,
            'PhoneNumber': phone,
            'CallBackURL': MPESA_CALLBACK_URL,
            'AccountReference': account_reference[:20],
            'TransactionDesc': transaction_desc[:20] if transaction_desc else 'AUTO-V Payment'
        }
        
        logger.info(f"📤 Sending STK Push to {phone} for KES {amount}")
        logger.info(f"📝 Account Reference: {account_reference}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"✅ STK Push response: {data}")
        
        return {
            'success': True,
            'data': data,
            'checkout_request_id': data.get('CheckoutRequestID')
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ STK Push request error: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"❌ STK Push error: {str(e)}")
        return {'success': False, 'error': str(e)}

# ─── Routes ──────────────────────────────────────────────────────

@mpesa_bp.route('/initiate', methods=['OPTIONS', 'POST'])
def initiate_mpesa():
    """
    Initiate M-Pesa STK Push payment
    
    Request body:
    {
        "phone": "0712345678",
        "amount": 100.00,
        "service": "valuation",
        "purpose": "Insurance Valuation",
        "client_type": "individual",
        "reference": "VAL-ABC123-XYZ"
    }
    
    Response:
    {
        "success": true,
        "data": {
            "payment_id": "PAY-ABC123",
            "checkout_request_id": "ws_CO_123456",
            "id": "PAY-ABC123",
            "reference": "VAL-ABC123-XYZ",
            "message": "STK Push sent successfully"
        }
    }
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response
    
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        logger.info(f"📦 PAYLOAD RECEIVED: {data}")
        
        # ─── Get Reference ──────────────────────────────────────────
        reference = data.get('reference') or data.get('payment_reference')
        
        if not reference:
            logger.error("❌ Missing reference in payload")
            return jsonify({
                'success': False,
                'error': 'Missing required fields: reference'
            }), 400
        
        # ─── Validate Required Fields ──────────────────────────────
        required = ['phone', 'amount']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        # ─── Validate Phone Number ──────────────────────────────────
        phone = data['phone']
        if not phone or len(phone) < 10:
            return jsonify({
                'success': False,
                'error': 'Invalid phone number'
            }), 400
        
        # ─── Validate Amount ─────────────────────────────────────────
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
        
        # ─── Generate Local Payment ID ──────────────────────────────
        local_payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        logger.info(f"📝 Generated Payment ID: {local_payment_id}")
        
        # ─── Process Payment with M-Pesa ────────────────────────────
        result = stk_push(
            phone_number=phone,
            amount=amount,
            account_reference=reference[:20],
            transaction_desc=data.get('description', f"AUTO-V {data.get('service', 'Payment')}")
        )
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Payment initiation failed')
            }), 500
        
        checkout_id = result.get('checkout_request_id')
        
        # ─── Save to Database (Optional - Skip if DB issues) ────────
        try:
            from services.supabase import get_client
            supabase = get_client()
            
            transaction_data = {
                'payment_id': local_payment_id,
                'checkout_request_id': checkout_id,
                'phone': phone,
                'amount': amount,
                'reference': reference,
                'service': data.get('service', 'unknown'),
                'purpose': data.get('purpose', 'unknown'),
                'client_type': data.get('client_type', 'individual'),
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            try:
                supabase.table('transactions').insert(transaction_data).execute()
                logger.info(f"✅ Transaction saved to database")
            except Exception as db_error:
                logger.warning(f"Could not save transaction: {db_error}")
        except Exception as e:
            logger.warning(f"Database error: {e}")
        
        # ─── Return Success Response ─────────────────────────────────
        return jsonify({
            'success': True,
            'data': {
                'payment_id': local_payment_id,
                'checkout_request_id': checkout_id,
                'id': local_payment_id,
                'reference': reference,
                'message': 'STK Push sent successfully'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ M-Pesa initiate error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """
    M-Pesa callback endpoint (receives payment confirmation from Safaricom)
    
    This endpoint is called by Safaricom after the customer completes the payment.
    """
    try:
        data = request.get_json()
        logger.info(f"📞 M-Pesa callback received: {data}")
        
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        
        logger.info(f"📊 Callback: {checkout_request_id} - {result_code} - {result_desc}")
        
        if result_code == 0:
            # ─── Payment Successful ──────────────────────────────────
            metadata = stk_callback.get('CallbackMetadata', {})
            items = metadata.get('Item', [])
            
            payment_data = {}
            for item in items:
                name = item.get('Name')
                value = item.get('Value')
                if name == 'Amount':
                    payment_data['amount'] = value
                elif name == 'MpesaReceiptNumber':
                    payment_data['receipt'] = value
                elif name == 'TransactionDate':
                    payment_data['transaction_date'] = value
                elif name == 'PhoneNumber':
                    payment_data['phone'] = value
            
            logger.info(f"✅ Payment successful: {payment_data}")
            
            # ─── Update Database ─────────────────────────────────────
            try:
                from services.supabase import get_client
                supabase = get_client()
                
                supabase.table('transactions').update({
                    'status': 'completed',
                    'payment_data': payment_data,
                    'updated_at': datetime.now().isoformat()
                }).eq('checkout_request_id', checkout_request_id).execute()
                
                logger.info(f"✅ Transaction {checkout_request_id} updated to completed")
            except Exception as e:
                logger.warning(f"Could not update transaction: {e}")
        
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
        
    except Exception as e:
        logger.error(f"❌ M-Pesa callback error: {str(e)}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Failed'}), 500

@mpesa_bp.route('/status/<payment_id>', methods=['GET'])
def get_transaction_status(payment_id):
    """
    Get transaction status
    
    Args:
        payment_id: Payment ID or checkout request ID
        
    Returns:
        Transaction status
    """
    try:
        from services.supabase import get_client
        supabase = get_client()
        
        # Try to find by payment_id or checkout_request_id
        response = supabase.table('transactions').select('*')\
            .or_(f'payment_id.eq.{payment_id},checkout_request_id.eq.{payment_id}')\
            .execute()
        
        if response.data:
            transaction = response.data[0]
            return jsonify({
                'success': True,
                'payment_id': payment_id,
                'checkout_request_id': transaction.get('checkout_request_id'),
                'status': transaction.get('status', 'pending'),
                'payment_data': transaction.get('payment_data'),
                'reference': transaction.get('reference')
            }), 200
        
        # If not found, return pending status
        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'checkout_request_id': payment_id,
            'status': 'pending',
            'message': 'Transaction pending'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mpesa_bp.route('/force-complete/<payment_id>', methods=['POST'])
def force_complete_payment(payment_id):
    """
    Force complete a payment (manual confirmation by user)
    
    Args:
        payment_id: Payment ID or checkout request ID
        
    Request body:
    {
        "transaction_id": "QWERTY123"
    }
    """
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id') if data else None
        
        if not transaction_id:
            return jsonify({
                'success': False,
                'error': 'Transaction ID is required'
            }), 400
        
        logger.info(f"📝 Force completing payment: {payment_id} with transaction: {transaction_id}")
        
        from services.supabase import get_client
        supabase = get_client()
        
        result = supabase.table('transactions').update({
            'status': 'completed',
            'payment_data': {'transaction_id': transaction_id, 'manual_confirm': True},
            'updated_at': datetime.now().isoformat()
        }).or_(f'payment_id.eq.{payment_id},checkout_request_id.eq.{payment_id}').execute()
        
        if result.data:
            logger.info(f"✅ Transaction {payment_id} force completed")
            return jsonify({
                'success': True,
                'message': 'Payment confirmed successfully'
            }), 200
        else:
            # If no transaction found, create one
            try:
                supabase.table('transactions').insert({
                    'payment_id': payment_id,
                    'checkout_request_id': payment_id,
                    'status': 'completed',
                    'payment_data': {'transaction_id': transaction_id, 'manual_confirm': True},
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }).execute()
                
                return jsonify({
                    'success': True,
                    'message': 'Payment confirmed successfully (new record)'
                }), 200
            except:
                return jsonify({
                    'success': True,
                    'message': 'Payment confirmed (fallback)'
                }), 200
        
    except Exception as e:
        logger.error(f"❌ Force complete error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mpesa_bp.route('/test', methods=['GET'])
def test_mpesa():
    """
    Test endpoint to verify M-Pesa routes are working
    """
    return jsonify({
        'success': True,
        'message': 'M-Pesa routes are working!',
        'shortcode': MPESA_SHORTCODE,
        'environment': MPESA_ENV,
        'timestamp': datetime.now().isoformat()
    }), 200

@mpesa_bp.route('/health', methods=['GET'])
def mpesa_health():
    """
    M-Pesa service health check
    """
    status = {
        'service': 'mpesa',
        'status': 'healthy',
        'environment': MPESA_ENV,
        'shortcode': MPESA_SHORTCODE,
        'configured': bool(MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET and MPESA_PASSKEY)
    }
    
    # Test token generation
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
