# app/services/mpesa.py
import base64
import hashlib
import hmac
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings

logger = logging.getLogger(__name__)

class MpesaService:
    """M-PESA integration service with async support"""
    
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.environment = settings.MPESA_ENVIRONMENT
        self.callback_url = settings.MPESA_CALLBACK_URL
        
        if self.environment == "production":
            self.base_url = "https://api.safaricom.co.ke"
        else:
            self.base_url = "https://sandbox.safaricom.co.ke"
        
        self.access_token = None
        self.token_expiry = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info(f"M-PESA service initialized in {self.environment} mode")
    
    async def get_access_token(self) -> str:
        """Get M-PESA access token asynchronously"""
        try:
            if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
                return self.access_token
            
            auth = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode()
            ).decode()
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                lambda: requests.get(
                    f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                    headers={"Authorization": f"Basic {auth}"},
                    timeout=30
                )
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get access token: {response.text}")
                raise Exception("Failed to get access token")
            
            data = response.json()
            self.access_token = data.get('access_token')
            self.token_expiry = datetime.utcnow().replace(second=0) + timedelta(seconds=3600)
            
            logger.info("M-PESA access token obtained successfully")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Access token error: {str(e)}")
            raise
    
    async def stk_push(
        self,
        amount: float,
        phone_number: str,
        account_reference: str,
        transaction_desc: str,
        transaction_type: str = "CustomerPayBillOnline"
    ) -> Dict[str, Any]:
        """Initiate STK Push payment asynchronously"""
        try:
            access_token = await self.get_access_token()
            
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            password = base64.b64encode(
                f"{self.shortcode}{self.passkey}{timestamp}".encode()
            ).decode()
            
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": transaction_type,
                "Amount": str(int(amount)),
                "PartyA": phone_number,
                "PartyB": self.shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": self.callback_url,
                "AccountReference": account_reference[:36],
                "TransactionDesc": transaction_desc[:36]
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                lambda: requests.post(
                    f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=60
                )
            )
            
            if response.status_code != 200:
                logger.error(f"STK Push failed: {response.text}")
                return {
                    'success': False,
                    'message': 'Payment initiation failed',
                    'response': response.text
                }
            
            data = response.json()
            
            if data.get('ResponseCode') != '0':
                return {
                    'success': False,
                    'message': data.get('ResponseDescription', 'Payment failed'),
                    'response': data
                }
            
            logger.info(f"STK Push initiated successfully: {data.get('CheckoutRequestID')}")
            return {
                'success': True,
                'message': 'Payment initiated successfully',
                'CheckoutRequestID': data.get('CheckoutRequestID'),
                'MerchantRequestID': data.get('MerchantRequestID'),
                'response': data
            }
            
        except Exception as e:
            logger.error(f"STK Push error: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    async def query_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """Query STK Push status asynchronously"""
        try:
            access_token = await self.get_access_token()
            
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            password = base64.b64encode(
                f"{self.shortcode}{self.passkey}{timestamp}".encode()
            ).decode()
            
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                lambda: requests.post(
                    f"{self.base_url}/mpesa/stkpushquery/v1/query",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=30
                )
            )
            
            if response.status_code != 200:
                logger.error(f"Query status failed: {response.text}")
                return {
                    'success': False,
                    'message': 'Failed to query payment status'
                }
            
            data = response.json()
            
            return {
                'success': True,
                'message': 'Status retrieved successfully',
                'ResultCode': data.get('ResultCode'),
                'ResultDesc': data.get('ResultDesc'),
                'response': data
            }
            
        except Exception as e:
            logger.error(f"Query status error: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    async def process_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process M-PESA callback"""
        try:
            body = callback_data.get('Body', {})
            stk_callback = body.get('stkCallback', {})
            
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            merchant_request_id = stk_callback.get('MerchantRequestID')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            
            callback_metadata = stk_callback.get('CallbackMetadata', {})
            items = callback_metadata.get('Item', [])
            
            metadata = {}
            for item in items:
                metadata[item.get('Name')] = item.get('Value')
            
            payment_status = 'completed' if result_code == '0' else 'failed'
            
            logger.info(f"Callback processed: {checkout_request_id} - {payment_status}")
            
            return {
                'success': result_code == '0',
                'result_code': result_code,
                'result_desc': result_desc,
                'merchant_request_id': merchant_request_id,
                'checkout_request_id': checkout_request_id,
                'metadata': metadata,
                'payment_status': payment_status
            }
            
        except Exception as e:
            logger.error(f"Callback processing error: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
