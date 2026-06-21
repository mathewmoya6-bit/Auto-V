# api/routes/mpesa.py - Complete M-Pesa Routes
from flask import Blueprint, request, jsonify, make_response
import logging
import os
import base64
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

mpesa_bp = Blueprint('mpesa', __name__)

# ─── M-PESA CONFIG ──────────────────────────────────────────────

MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', 'LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', 'aGGo8AuPJVpsZLcs')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://auto-v-backend.onrender.com/api/mpesa/callback')
MPESA_ENV = os.getenv('MPESA_ENV', 'production')

if MPESA_ENV == 'production':
    MPESA_API_URL = 'https://api.safaricom.co.ke'
else:
    MPESA_API_URL = 'https://sandbox.safaricom.co.ke'

# ─── HELPERS ──────────────────────────────────────────────────────

def get_mpesa_token():
    """Get M-Pesa OAuth token"""
    try:
        credentials = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        url = f"{MPESA_API_URL}/oauth/v1/generate?grant_type=client_credentials"
        headers = {'Authorization': f'Basic {encoded}'}
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data.get('access_token')
    except Exception as e:
        logger.error(f"MPesa token error: {str(e)}")
        return None

def stk_push(phone_number, amount, account_reference, transaction_desc):
    """Send STK Push to customer"""
    try:
        token = get_mpesa_token()
        if not token:
            return {'success': False, 'error': 'Failed to get M-Pesa token'}
        
        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+254'):
            phone_number = phone_number[1:]
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
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
            'TransactionDesc': transaction_desc[:20]
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            'success': True,
            'data': data,
            'checkout_request_id': data.get('CheckoutRequestID')
        }
    except Exception as e:
        logger.error(f"STK Push error: {str(e)}")
        return {'success': False, 'error': str(e)}

# ─── ROUTES ──────────────────────────────────────────────────────

@mpesa_bp.route('/initiate', methods=['OPTIONS', 'POST'])
def initiate_mpesa():
    """Initiate M-Pesa STK Push"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, PUT, POST, DELETE, OPTIONS')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required = ['phone', 'amount', 'reference']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing fields: {", ".join(missing)}'
            }), 400
        
        # Process payment
        result = stk_push(
            phone_number=data['phone'],
            amount=data['amount'],
            account_reference=data['reference'],
            transaction_desc=data.get('description', 'AUTO-V Payment')
        )
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Payment initiation failed')
            }), 500
        
        return jsonify({
            'success': True,
            'data': {
                'checkout_request_id': result.get('checkout_request_id'),
                'message': 'STK Push sent successfully'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"MPesa initiate error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """M-Pesa callback endpoint"""
    try:
        data = request.get_json()
        logger.info(f"M-Pesa callback received: {data}")
        
        # Process callback here
        # Update transaction status in database
        
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
    except Exception as e:
        logger.error(f"MPesa callback error: {str(e)}", exc_info=True)
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Failed'}), 500

@mpesa_bp.route('/status/<checkout_request_id>', methods=['GET'])
def get_transaction_status(checkout_request_id):
    """Get transaction status"""
    return jsonify({
        'success': True,
        'checkout_request_id': checkout_request_id,
        'status': 'pending'
    }), 200

# ─── TEST ROUTE ──────────────────────────────────────────────────

@mpesa_bp.route('/test', methods=['GET'])
def test_mpesa():
    """Test endpoint to check if routes are working"""
    return jsonify({
        'success': True,
        'message': 'M-Pesa routes are working!',
        'shortcode': MPESA_SHORTCODE,
        'environment': MPESA_ENV
    }), 200
