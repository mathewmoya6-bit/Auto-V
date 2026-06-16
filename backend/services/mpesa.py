import requests
import base64
import json
from datetime import datetime
from typing import Optional
from config import settings
from services.logger import logger

class MpesaService:
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.callback_url = settings.MPESA_CALLBACK_URL
        self.base_url = "https://api.safaricom.co.ke"
        self.token = None
        self.token_expiry = None
    
    def _get_access_token(self) -> str:
        try:
            auth_url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            auth = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode()
            ).decode()
            
            headers = {"Authorization": f"Basic {auth}"}
            response = requests.get(auth_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                logger.info("M-Pesa access token obtained")
                return self.token
            else:
                logger.error(f"Failed to get M-Pesa token: {response.text}")
                raise Exception("Failed to get M-Pesa token")
        except Exception as e:
            logger.error(f"M-Pesa token error: {str(e)}")
            raise
    
    def stk_push(self, phone: str, amount: float, account_reference: str = "AUTO-V"):
        try:
            token = self._get_access_token()
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            password = base64.b64encode(
                f"{self.shortcode}{self.passkey}{timestamp}".encode()
            ).decode()
            
            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
            
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone,
                "PartyB": self.shortcode,
                "PhoneNumber": phone,
                "CallBackURL": self.callback_url,
                "AccountReference": account_reference,
                "TransactionDesc": f"Payment for {account_reference}"
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"STK Push initiated: {data}")
                return data
            else:
                logger.error(f"STK Push failed: {response.text}")
                raise Exception("STK Push failed")
        except Exception as e:
            logger.error(f"STK Push error: {str(e)}")
            raise
    
    async def handle_successful_payment(self, checkout_request_id: str, data: dict):
        from services.supabase_client import supabase
        
        payment = supabase.table("payments")\\
            .select("*")\\
            .eq("transaction_id", checkout_request_id)\\
            .single()\\
            .execute()
        
        if payment.data:
            supabase.table("payments")\\
                .update({
                    "status": "approved",
                    "mpesa_data": data,
                    "approved_at": datetime.now().isoformat()
                })\\
                .eq("id", payment.data["id"])\\
                .execute()
            
            logger.info(f"Payment {checkout_request_id} approved")
    
    async def handle_failed_payment(self, checkout_request_id: str, data: dict):
        from services.supabase_client import supabase
        
        payment = supabase.table("payments")\\
            .select("*")\\
            .eq("transaction_id", checkout_request_id)\\
            .single()\\
            .execute()
        
        if payment.data:
            supabase.table("payments")\\
                .update({
                    "status": "rejected",
                    "mpesa_data": data,
                    "rejected_at": datetime.now().isoformat()
                })\\
                .eq("id", payment.data["id"])\\
                .execute()
            
            logger.info(f"Payment {checkout_request_id} rejected")

mpesa_service = MpesaService()
