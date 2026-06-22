import os
import base64
import requests
import uuid
import logging
from datetime import datetime, timedelta

from services.supabase_client import create_payment, get_payment_by_checkout_id, update_payment

logger = logging.getLogger(__name__)

MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")

BASE_URL = "https://api.safaricom.co.ke"


_token = {"value": None, "expires": None}


def get_token():
    global _token

    if _token["value"] and _token["expires"] and datetime.now() < _token["expires"]:
        return _token["value"]

    auth = base64.b64encode(f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()).decode()

    res = requests.get(
        f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {auth}"}
    )

    token = res.json().get("access_token")

    _token = {
        "value": token,
        "expires": datetime.now() + timedelta(seconds=3500)
    }

    return token


# ─── STK PUSH ─────────────────────────────
def initiate_stk_push(phone, amount, payment_id, **kwargs):

    token = get_token()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()
    ).decode()

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": payment_id,
        "TransactionDesc": "Payment"
    }

    res = requests.post(
        f"{BASE_URL}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    data = res.json()

    checkout_id = data.get("CheckoutRequestID")

    create_payment({
        "payment_id": payment_id,
        "amount": amount,
        "phone": phone,
        "checkout_request_id": checkout_id,
        "status": "pending"
    })

    return {
        "checkout_request_id": checkout_id,
        "merchant_request_id": data.get("MerchantRequestID"),
        "payment_id": payment_id
    }


# ─── CALLBACK ─────────────────────────────
def handle_mpesa_callback(data):

    stk = data.get("Body", {}).get("stkCallback", {})

    checkout_id = stk.get("CheckoutRequestID")
    result_code = str(stk.get("ResultCode"))

    payment = get_payment_by_checkout_id(checkout_id)

    if not payment:
        return {"ResultCode": 1, "ResultDesc": "Not found"}

    if result_code == "0":
        items = stk.get("CallbackMetadata", {}).get("Item", [])

        receipt = None

        for i in items:
            if i["Name"] == "MpesaReceiptNumber":
                receipt = i["Value"]

        update_payment(payment["id"], {
            "status": "completed",
            "mpesa_code": receipt,
            "paid_at": datetime.now().isoformat()
        })

    else:
        update_payment(payment["id"], {"status": "failed"})

    return {"ResultCode": 0, "ResultDesc": "OK"}
