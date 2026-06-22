# api/routes/mpesa.py - Production Ready v3

import os
import logging
import uuid
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
from services.supabase_client import (
    get_supabase_client,
    get_payment_by_id,
    get_payment_by_custom_id,
    get_payment_by_checkout_id,
    get_payment_by_mpesa_code,
    update_payment,
    update_payment_by_custom_id,
    get_user_payments
)

logger = logging.getLogger(__name__)

mpesa_bp = Blueprint("mpesa", __name__)

MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
MPESA_ENV = os.getenv('MPESA_ENV', 'production')


def response(success: bool, data: dict = None, error: str = None, status: int = 200):
    """Standardized API response format."""
    result = {"success": success}
    if data is not None:
        result["data"] = data
    if error is not None:
        result["error"] = error
    return jsonify(result), status


@mpesa_bp.route("/initiate", methods=["POST", "OPTIONS"])
def initiate_payment():
    """Initiate M-Pesa STK Push payment."""
    try:
        if request.method == "OPTIONS":
            return response(True, {"status": "ok"})

        data = request.get_json()
        
        if not data:
            return response(False, error="No data provided", status=400)

        if "phone" not in data or "amount" not in data:
            return response(False, error="Phone and amount are required", status=400)

        # Generate IDs
        payment_id = data.get("payment_id") or f"PAY-{uuid.uuid4().hex[:8].upper()}"
        reference = data.get("reference") or f"AUTO-{uuid.uuid4().hex[:8].upper()}"
        user_id = data.get("user_id")
        request_id = data.get("request_id")

        # Parse amount
        try:
            amount = float(data["amount"])
            if amount <= 0:
                raise ValueError
        except:
            return response(False, error="Amount must be a positive number", status=400)

        # Normalize phone
        phone = data["phone"]
        if not phone or len(phone) < 10:
            return response(False, error="Invalid phone number", status=400)

        logger.info(f"📝 Processing payment: {payment_id} for {phone} - KES {amount}")

        # Initiate STK Push
        result = initiate_stk_push(
            phone=phone,
            amount=amount,
            payment_id=payment_id,
            reference=reference,
            user_id=user_id,
            request_id=request_id
        )

        return response(True, {
            "payment_id": payment_id,
            "checkout_request_id": result.get("checkout_request_id"),
            "merchant_request_id": result.get("merchant_request_id"),
            "reference": reference,
            "message": "STK Push sent successfully"
        })

    except Exception as e:
        logger.error(f"❌ Payment initiation error: {str(e)}", exc_info=True)
        return response(False, error=str(e), status=500)


@mpesa_bp.route("/status/<payment_id>", methods=["GET", "OPTIONS"])
def get_payment_status(payment_id):
    """Get payment status by payment_id or ID."""
    try:
        if request.method == "OPTIONS":
            return response(True, {"status": "ok"})

        client = get_supabase_client()

        # Try by payment_id first
        result = client.table("payments").select("*").eq("payment_id", payment_id).execute()
        
        if result.data:
            return response(True, result.data[0])

        # Try by checkout_request_id
        payment = get_payment_by_checkout_id(payment_id)
        if payment:
            return response(True, payment)

        # Try by mpesa_code
        payment = get_payment_by_mpesa_code(payment_id)
        if payment:
            return response(True, payment)

        # Try by UUID
        try:
            uuid.UUID(payment_id)
            payment = get_payment_by_id(payment_id)
            if payment:
                return response(True, payment)
        except:
            pass

        return response(True, {"status": "not_found", "payment_id": payment_id})

    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
        return response(False, error=str(e), status=500)


@mpesa_bp.route("/callback", methods=["POST"])
def mpesa_callback():
    """M-Pesa callback endpoint."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"ResultCode": 1, "ResultDesc": "No data"}), 200

        logger.info("📞 M-Pesa callback received")
        result = handle_mpesa_callback(data)
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"❌ Callback error: {str(e)}")
        return jsonify({"ResultCode": 1, "ResultDesc": "System error"}), 200


@mpesa_bp.route("/auto-confirm/<payment_id>", methods=["POST", "OPTIONS"])
def auto_confirm(payment_id):
    """Auto-confirm payment by verifying with M-Pesa API."""
    try:
        if request.method == "OPTIONS":
            return response(True, {"status": "ok"})

        # First try to find by custom payment_id
        payment = get_payment_by_custom_id(payment_id)
        
        if not payment:
            try:
                uuid.UUID(payment_id)
                payment = get_payment_by_id(payment_id)
            except ValueError:
                pass

        if not payment:
            return response(False, error="Payment not found", status=404)

        actual_uuid = payment.get("id")
        result = auto_confirm_payment(actual_uuid)
        
        return response(result.get("success"), data=result)

    except Exception as e:
        logger.error(f"❌ Auto-confirm error: {str(e)}", exc_info=True)
        return response(False, error=str(e), status=500)


@mpesa_bp.route("/user/<user_id>", methods=["GET"])
def get_user_payments_route(user_id):
    """Get all payments for a user."""
    try:
        limit = request.args.get('limit', 50, type=int)
        payments = get_user_payments(user_id, limit)
        return response(True, {"payments": payments, "count": len(payments)})
    except Exception as e:
        logger.error(f"❌ Get user payments error: {str(e)}")
        return response(False, error="Failed to get user payments", status=500)


@mpesa_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "mpesa",
        "environment": MPESA_ENV,
        "shortcode": MPESA_SHORTCODE,
        "configured": is_mpesa_configured(),
        "timestamp": datetime.now().isoformat()
    }), 200


@mpesa_bp.route("/test", methods=["GET"])
def test_endpoint():
    """Test endpoint."""
    return response(True, {
        "message": "M-Pesa routes are working",
        "environment": MPESA_ENV,
        "shortcode": MPESA_SHORTCODE,
        "timestamp": datetime.now().isoformat()
    })
