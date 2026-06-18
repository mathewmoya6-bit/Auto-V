import os
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
from services.supabase_client import get_supabase

load_dotenv()

MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://auto-v.onrender.com/api/payments/callback')
BASE_URL = os.getenv('MPESA_ENV', 'sandbox') == 'sandbox' \
    and 'https://sandbox.safaricom.co.ke' \
    or 'https://api.safaricom.co.ke'

def get_mpesa_token():
    auth = base64.b64encode(f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()).decode()
    headers = {'Authorization': f'Basic {auth}'}
    url = f'{BASE_URL}/oauth/v1/generate?grant_type=client_credentials'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get('access_token')

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
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def handle_mpesa_callback(callback_data):
    stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
    result_code = stk_callback.get('ResultCode')
    result_desc = stk_callback.get('ResultDesc')
    checkout_id = stk_callback.get('CheckoutRequestID')

    supabase = get_supabase()
    resp = supabase.table('payments')\
        .select('*')\
        .eq('mpesa_checkout_id', checkout_id)\
        .execute()
    if not resp.data:
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
