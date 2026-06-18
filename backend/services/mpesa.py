# services/mpesa.py – Core M-Pesa Logic

import os
import base64
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
load_dotenv()

# ─── Environment Variables ──────────────────────────────────
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', '')
MPESA_ENV = os.getenv('MPESA_ENV', 'sandbox').lower()

BASE_URL = 'https://sandbox.safaricom.co.ke' if MPESA_ENV == 'sandbox' else 'https://api.safaricom.co.ke'

REQUEST_TIMEOUT = 15
MAX_TOKEN_RETRIES = 3
_token_cache = {'token': None, 'expires_at': None}

def is_mpesa_configured() -> bool:
    """Check if all M-Pesa credentials are set."""
    return all([MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET, MPESA_PASSKEY, MPESA_SHORTCODE, CALLBACK_URL])

def normalize_phone(phone: str) -> str:
    """Normalize phone number to international format."""
    if not phone:
        raise ValueError("Phone number is required")
    
    phone = ''.join(ch for ch in phone if ch.isdigit() or ch == '+')
    
    if phone.startswith('+'):
        phone = phone[1:]
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    if len(phone) == 9 and phone.startswith('7'):
        phone = '254' + phone
    if phone.startswith('254') and len(phone) == 12:
        return phone
    if len(phone) == 10 and phone.startswith('7'):
        return '254' + phone
    
    raise ValueError(f"Invalid phone number format: {phone}")

def get_mpesa_token(force_refresh: bool = False) -> str:
    """Obtain OAuth token from Safaricom."""
    global _token_cache
    
    if not force_refresh and _token_cache.get('token'):
        if _token_cache.get('expires_at') and datetime.now() < _token_cache['expires_at']:
            return _token_cache['token']
    
    if not MPESA_CONSUMER_KEY or not MPESA_CONSUMER_SECRET:
        raise ValueError("M-Pesa Consumer Key and Secret must be set")
    
    auth = base64.b64encode(f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()).decode()
    headers = {'Authorization': f'Basic {auth}'}
    url = f'{BASE_URL}/oauth/v1/generate?grant_type=client_credentials'
    
    retries = 0
    while retries < MAX_TOKEN_RETRIES:
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            token = data.get('access_token')
            if not token:
                raise Exception("No access_token in response")
            
            expires_in = data.get('expires_in', 3600) - 300
            _token_cache = {
                'token': token,
                'expires_at': datetime.now() + timedelta(seconds=max(expires_in, 60))
            }
            logger.info("✅ M-Pesa token obtained successfully")
            return token
            
        except requests.exceptions.RequestException as e:
            retries += 1
            wait_time = 2 ** retries
            logger.warning(f"Token request failed (attempt {retries}/{MAX_TOKEN_RETRIES}): {e}")
            time.sleep(wait_time)
    
    raise Exception("Failed to obtain M-Pesa token after maximum retries")

def initiate_stk_push(phone: str, amount: float, payment_id: str, service: str = 'AUTO-V') -> Dict[str, Any]:
    """Initiate STK Push to customer's phone."""
    if not is_mpesa_configured():
        raise Exception("M-Pesa is not configured")
    
    token = get_mpesa_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()
    phone = normalize_phone(phone)
    
    payload = {
        'BusinessShortCode': MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': int(round(amount)),
        'PartyA': phone,
        'PartyB': MPESA_SHORTCODE,
        'PhoneNumber': phone,
        'CallBackURL': CALLBACK_URL,
        'AccountReference': f'AUTO-{payment_id[:6]}',
        'TransactionDesc': f'Payment for {service}'
    }
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    url = f'{BASE_URL}/mpesa/stkpush/v1/processrequest'
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data.get('ResponseCode') != '0':
            raise Exception(f"STK Push failed: {data.get('ResponseDescription')}")
        
        return data
    except Exception as e:
        raise Exception(f"STK Push error: {str(e)}")

def query_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    """Query the status of an STK Push transaction."""
    token = get_mpesa_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()
    
    payload = {
        'BusinessShortCode': MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'CheckoutRequestID': checkout_request_id
    }
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    url = f'{BASE_URL}/mpesa/stkpushquery/v1/query'
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to query payment status: {str(e)}")
