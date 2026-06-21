# api/routes/mpesa.py - M-Pesa Routes (Production Ready)
import os
import time
import logging
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
    except Exception as e:
        logger.error(f"❌ M-Pesa token error: {str(e)}")
        return None

def stk_push(phone_number, amount, account_reference, transaction_desc):
    """
    Send STK Push to customer
    """
    try:
        # Get token
        token = get_mpesa_token()
        if not token:
            return {'success': False, 'error': 'Failed to get M-Pesa token'}
        
        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+254'):
            phone_number = phone_number[1:]
        elif phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
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
            'PartyA': phone_number,
            'PartyB': MPESA_SHORTCODE,
            'PhoneNumber': phone_number,
            'CallBackURL': MPESA_CALLBACK_URL,
            'AccountReference': account_reference[:20],
            'TransactionDesc': transaction_desc[:20] if transaction_desc else 'AUTO-V Payment'
        }
        
        logger.info(f"📤 Sending STK Push to {phone_number} for KES {amount}")
        
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
        
        # Validate required fields
        required = ['phone', 'amount', 'reference']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        # Validate phone number
        phone = data['phone']
        if not phone or len(phone) < 10:
            return jsonify({
                'success': False,
                'error': 'Invalid phone number'
            }), 400
        
        # Validate amount
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
        
        # Process payment
        result = stk_push(
            phone_number=phone,
            amount=amount,
            account_reference=data['reference'],
            transaction_desc=data.get('description', 'AUTO-V Payment')
        )
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Payment initiation failed')
            }), 500
        
        # Return success response
        return jsonify({
            'success': True,
            'data': {
                'checkout_request_id': result.get('checkout_request_id'),
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
    M-Pesa callback endpoint (receives payment confirmation)
    """
    try:
        data = request.get_json()
        logger.info(f"📞 M-Pesa callback received: {data}")
        
        # Extract callback data
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        
        logger.info(f"📊 Callback: {checkout_request_id} - {result_code} - {result_desc}")
        
        # If successful, extract payment details
        if result_code == 0:
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
            
            # Here you would update your database
            # supabase.table('transactions').update({'status': 'completed'}).eq('checkout_request_id', checkout_request_id).execute()
        
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
        
    except Exception as e:
        logger.error(f"❌ M-Pesa callback error: {str(e)}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Failed'}), 500

@mpesa_bp.route('/status/<checkout_request_id>', methods=['GET'])
def get_transaction_status(checkout_request_id):
    """
    Get transaction status
    """
    try:
        # Here you would check database for transaction status
        # supabase.table('transactions').select('*').eq('checkout_request_id', checkout_request_id).execute()
        
        return jsonify({
            'success': True,
            'checkout_request_id': checkout_request_id,
            'status': 'pending',  # pending, completed, failed
            'message': 'Transaction status retrieved'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
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

# ─── Health Check ──────────────────────────────────────────────

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
