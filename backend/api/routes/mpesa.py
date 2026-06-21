# api/routes/mpesa.py - M-Pesa Payment Routes
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import json
import requests
import base64
import os

from services.supabase_client import get_supabase
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

mpesa_bp = Blueprint('mpesa', __name__)

# ─── M-PESA CONFIGURATION ──────────────────────────────────────

MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', 'LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', 'aGGo8AuPJVpsZLcs')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://auto-v-backend.onrender.com/api/mpesa/callback')
MPESA_ENV = os.getenv('MPESA_ENV', 'production')

# MPesa API URLs
if MPESA_ENV == 'production':
    MPESA_API_URL = 'https://api.safaricom.co.ke'
else:
    MPESA_API_URL = 'https://sandbox.safaricom.co.ke'

# ─── HELPERS ────────────────────────────────────────────────────

def get_mpesa_token():
    """Get M-Pesa OAuth token"""
    try:
        # Encode credentials
        credentials = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        # Get token
        url = f"{MPESA_API_URL}/oauth/v1/generate?grant_type=client_credentials"
        headers = {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/json'
        }
        
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
        
        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Generate password
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
            'AccountReference': account_reference,
            'TransactionDesc': transaction_desc[:20]  # Max 20 chars
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

# ─── ROUTES ──────────────────────────────────────────────────

@mpesa_bp.route('/stk-push', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def stk_push_request():
    """Initiate STK Push payment"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required = ['phone_number', 'amount', 'account_reference']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing fields: {", ".join(missing)}'
            }), 400
        
        # Process payment
        result = stk_push(
            phone_number=data['phone_number'],
            amount=data['amount'],
            account_reference=data['account_reference'],
            transaction_desc=data.get('transaction_desc', 'AUTO-V Payment')
        )
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Payment initiation failed')
            }), 500
        
        # Save transaction
        supabase = get_supabase()
        supabase.save_transaction({
            'checkout_request_id': result.get('checkout_request_id'),
            'phone_number': data['phone_number'],
            'amount': data['amount'],
            'account_reference': data['account_reference'],
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'data': {
                'checkout_request_id': result.get('checkout_request_id'),
                'message': 'STK Push sent successfully'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"STK Push error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@mpesa_bp.route('/callback', methods=['POST'])
@log_request
def mpesa_callback():
    """M-Pesa callback endpoint"""
    try:
        data = request.get_json()
        logger.info(f"M-Pesa callback received: {json.dumps(data)}")
        
        # Extract data
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        callback_metadata = stk_callback.get('CallbackMetadata', {})
        
        # Update transaction
        supabase = get_supabase()
        
        if result_code == 0:
            # Success - extract payment details
            items = callback_metadata.get('Item', [])
            payment_data = {}
            
            for item in items:
                name = item.get('Name')
                value = item.get('Value')
                if name == 'Amount':
                    payment_data['amount'] = value
                elif name == 'MpesaReceiptNumber':
                    payment_data['receipt_number'] = value
                elif name == 'TransactionDate':
                    payment_data['transaction_date'] = value
                elif name == 'PhoneNumber':
                    payment_data['phone_number'] = value
            
            # Update transaction as successful
            supabase.update_transaction_status(
                checkout_request_id,
                'completed',
                result_desc,
                payment_data
            )
            
        else:
            # Failed transaction
            supabase.update_transaction_status(
                checkout_request_id,
                'failed',
                result_desc
            )
        
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
        
    except Exception as e:
        logger.error(f"M-Pesa callback error: {str(e)}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Failed'}), 500

@mpesa_bp.route('/status/<checkout_request_id>', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_transaction_status(checkout_request_id):
    """Get transaction status"""
    try:
        supabase = get_supabase()
        result = supabase.get_transaction(checkout_request_id)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
    except Exception as e:
        logger.error(f"Get transaction error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@mpesa_bp.route('/balance', methods=['GET'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def get_balance():
    """Get M-Pesa balance (admin only)"""
    try:
        # This would require M-Pesa account balance API
        return jsonify({
            'success': True,
            'data': {
                'message': 'Balance check endpoint',
                'note': 'Implement M-Pesa balance API'
            }
        }), 200
    except Exception as e:
        logger.error(f"Get balance error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
