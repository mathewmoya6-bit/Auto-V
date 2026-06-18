import os
import base64
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
load_dotenv()

MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL')
BASE_URL = os.getenv('MPESA_ENV', 'sandbox') == 'sandbox' \
    and 'https://sandbox.safaricom.co.ke' \
    or 'https://api.safaricom.co.ke'

def get_mpesa_token():
    auth = base64.b64encode(f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()).decode()
    headers = {'Authorization': f'Basic {auth}'}
    url = f'{BASE_URL}/oauth/v1/generate?grant_type=client_credentials'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        token = response.json().get('access_token')
        logger.info("M-Pesa token obtained")
        return token
    except Exception as e:
        logger.error(f"Failed to get M-Pesa token: {e}")
        raise

def initiate_stk_push(phone, amount, payment_id, reference=None, service='AUTO-V'):
    token = get_mpesa_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(
        f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()
    ).decode()

    phone = phone.strip()
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    phone = phone.replace('+', '')

    payload = {
        'BusinessShortCode': MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': int(amount),
        'PartyA': phone,
        'PartyB': MPESA_SHORTCODE,
        'PhoneNumber': phone,
        'CallBackURL': CALLBACK_URL,
        'AccountReference': reference or f'AUTO-{payment_id[:6]}',
        'TransactionDesc': f'Payment for {service}'
    }

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    url = f'{BASE_URL}/mpesa/stkpush/v1/processrequest'
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"STK Push sent for payment {payment_id}")
        return response.json()
    except Exception as e:
        logger.error(f"STK Push request failed: {e}")
        raise

def handle_mpesa_callback(callback_data):
    stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
    result_code = stk_callback.get('ResultCode')
    result_desc = stk_callback.get('ResultDesc')
    checkout_id = stk_callback.get('CheckoutRequestID')

    logger.info(f"Processing callback for checkout {checkout_id}, result: {result_code}")

    supabase = get_supabase()
    resp = supabase.table('payments')\
        .select('*')\
        .eq('mpesa_checkout_id', checkout_id)\
        .execute()
    if not resp.data:
        logger.error(f"Payment not found for checkout ID: {checkout_id}")
        raise Exception(f'Payment not found for checkout ID: {checkout_id}')

    payment = resp.data[0]
    status = 'completed' if result_code == '0' else 'failed'
    update_data = {
        'status': status,
        'mpesa_result_code': result_code,
        'mpesa_result_desc': result_desc
    }
    if status == 'completed':
        update_data['completed_at'] = datetime.now().isoformat()

    supabase.table('payments').update(update_data).eq('id', payment['id']).execute()
    logger.info(f"Payment {payment['id']} updated to {status}")
