from flask import Blueprint, request, jsonify
import uuid
import logging

from services.mpesa import initiate_stk_push, handle_mpesa_callback
from services.supabase_client import (
    get_payment_by_custom_id,
    get_payment_by_checkout_id,
    get_payment_by_mpesa_code,
    get_payment_by_id,
    get_supabase_client
)

logger = logging.getLogger(__name__)

mpesa_bp = Blueprint("mpesa", __name__)


def response(ok, data=None, error=None):
    return jsonify({"success": ok, "data": data, "error": error})


@mpesa_bp.route("/initiate", methods=["POST"])
def initiate():
    data = request.get_json()

    payment_id = data.get("payment_id") or f"PAY-{uuid.uuid4().hex[:8]}"
    phone = data["phone"]
    amount = float(data["amount"])

    result = initiate_stk_push(phone, amount, payment_id)

    return response(True, result)


@mpesa_bp.route("/status/<payment_id>")
def status(payment_id):

    client = get_supabase_client()

    res = client.table("payments").select("*").eq("payment_id", payment_id).execute()

    if res.data:
        return response(True, res.data[0])

    return response(True, {"status": "not_found"})


@mpesa_bp.route("/callback", methods=["POST"])
def callback():
    data = request.get_json(silent=True)
    return jsonify(handle_mpesa_callback(data))


@mpesa_bp.route("/health")
def health():
    return jsonify({"status": "ok", "service": "mpesa"})
