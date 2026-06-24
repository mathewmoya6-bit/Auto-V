# ============================================================
# api/routes/mpesa.py - M-Pesa Routes (Flask)
# ============================================================

import os
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from services.mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    query_payment_status,
    auto_confirm_payment,
    is_mpesa_configured,
    get_mpesa_token
)

logger = logging.getLogger(__name__)

# ─── Blueprint ──────────────────────────────────────────────
mpesa_bp = Blueprint("mpesa", __name__, url_prefix="/api/mpesa")


# ─── Response Helper ──────────────────────────────────────
def response(success: bool, data=None, error=None, status=200):
    """Standard API response wrapper."""
    payload = {"success": success}
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    return jsonify(payload), status


# ─── Routes ──────────────────────────────────────────────

@mpesa_bp.route("/initiate", methods=["POST", "OPTIONS"])
def initiate_payment():
    """Initiate M-Pesa STK Push payment."""
    # Handle preflight
    if request.method == "OPTIONS":
        return response(True, {"status": "ok"})

    try:
        data = request.get_json()
        if not data:
            return response(False, error="Missing data", status=400)

        phone = data.get("phone")
        amount = data.get("amount")

        if not phone or not amount:
            return response(False, error="Phone and amount required", status=400)

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError()
        except:
            return response(False, error="Invalid amount", status=400)

        payment_id = data.get("payment_id") or f"PAY-{uuid.uuid4().hex[:8].upper()}"
        reference = data.get("reference") or f"AUTO-{uuid.uuid4().hex[:8].upper()}"

        logger.info(f"📤 Payment init: {payment_id} | {phone} | {amount}")

        result = initiate_stk_push(
            phone=phone,
            amount=amount,
            payment_id=payment_id,
            reference=reference,
            user_id=data.get("user_id")
        )

        return response(True, {
            "payment_id": payment_id,
            "checkout_request_id": result.get("CheckoutRequestID"),
            "merchant_request_id": result.get("MerchantRequestID")
        })

    except Exception as e:
        logger.error(f"initiate error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)


@mpesa_bp.route("/status/<payment_id>", methods=["GET", "OPTIONS"])
def get_payment_status(payment_id):
    """Get payment status by ID."""
    if request.method == "OPTIONS":
        return response(True, {"status": "ok"})

    try:
        # For now, return a mock status
        # In production, you would query the database or Safaricom
        return response(True, {
            "payment_id": payment_id,
            "status": "pending",
            "message": "Payment status retrieved"
        })
    except Exception as e:
        logger.error(f"status error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)


@mpesa_bp.route("/callback", methods=["POST"])
def mpesa_callback():
    """Handle M-Pesa callback from Safaricom."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"ResultCode": 1, "ResultDesc": "No data"}), 200

        logger.info(f"📩 Callback received")

        result = handle_mpesa_callback(data)
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"callback error: {e}", exc_info=True)
        return jsonify({"ResultCode": 1, "ResultDesc": "System error"}), 200


@mpesa_bp.route("/auto-confirm/<payment_id>", methods=["POST", "OPTIONS"])
def auto_confirm(payment_id):
    """Auto-confirm a pending payment."""
    if request.method == "OPTIONS":
        return response(True, {"status": "ok"})

    try:
        result = auto_confirm_payment(payment_id)
        return response(True, result)

    except Exception as e:
        logger.error(f"auto-confirm error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)


@mpesa_bp.route("/user/<user_id>", methods=["GET"])
def user_payments(user_id):
    """Get all payments for a user."""
    try:
        limit = request.args.get("limit", 50, type=int)
        # In production, query the database
        return response(True, {
            "user_id": user_id,
            "payments": [],
            "total": 0
        })
    except Exception as e:
        return response(False, error=str(e), status=500)


@mpesa_bp.route("/query/<checkout_request_id>", methods=["GET"])
def query_status(checkout_request_id):
    """Query payment status from Safaricom."""
    try:
        result = query_payment_status(checkout_request_id)
        return response(True, result)
    except Exception as e:
        logger.error(f"query error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)


@mpesa_bp.route("/test", methods=["GET"])
def test():
    """Test endpoint to verify M-Pesa API is working."""
    return response(True, {
        "message": "M-Pesa API working",
        "env": os.getenv("MPESA_ENV", "production"),
        "shortcode": os.getenv("MPESA_SHORTCODE", "4095377"),
        "configured": is_mpesa_configured()
    })


@mpesa_bp.route("/health", methods=["GET"])
def health():
    """Health check for M-Pesa service."""
    return jsonify({
        "status": "ok",
        "service": "mpesa",
        "environment": os.getenv("MPESA_ENV", "production"),
        "shortcode": os.getenv("MPESA_SHORTCODE", "4095377"),
        "configured": is_mpesa_configured(),
        "timestamp": datetime.utcnow().isoformat()
    })


@mpesa_bp.route("/routes", methods=["GET"])
def list_routes():
    """Debug: List all registered M-Pesa routes."""
    return jsonify({
        "routes": [
            {"path": "/api/mpesa/initiate", "method": "POST"},
            {"path": "/api/mpesa/status/{payment_id}", "method": "GET"},
            {"path": "/api/mpesa/callback", "method": "POST"},
            {"path": "/api/mpesa/auto-confirm/{payment_id}", "method": "POST"},
            {"path": "/api/mpesa/user/{user_id}", "method": "GET"},
            {"path": "/api/mpesa/query/{checkout_request_id}", "method": "GET"},
            {"path": "/api/mpesa/health", "method": "GET"},
            {"path": "/api/mpesa/test", "method": "GET"},
            {"path": "/api/mpesa/routes", "method": "GET"}
        ],
        "total": 9,
        "base_url": "/api/mpesa"
    })
