# api/routes/mpesa.py - Clean Production Version

from flask import Blueprint, request, jsonify
import uuid
import logging
from datetime import datetime

from services.mpesa import initiate_stk_push, handle_mpesa_callback
from services.supabase_client import (
    get_payment_by_custom_id,
    get_payment_by_checkout_id,
    get_payment_by_mpesa_code,
    get_payment_by_id,
    get_supabase_client,
    create_payment,
    update_payment
)

logger = logging.getLogger(__name__)

mpesa_bp = Blueprint("mpesa", __name__)


def response(success=True, data=None, error=None, status=200):
    """Standardized response format."""
    result = {"success": success}
    if data is not None:
        result["data"] = data
    if error is not None:
        result["error"] = error
    return jsonify(result), status


@mpesa_bp.route("/initiate", methods=["POST", "OPTIONS"])
def initiate_payment():
    """Initiate M-Pesa STK Push."""
    try:
        # Handle preflight
        if request.method == "OPTIONS":
            return response(True, {"status": "ok"})

        data = request.get_json()
        
        if not data:
            return response(False, error="No data provided", status=400)

        # Validate required fields
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
        # Handle preflight
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


@mpesa_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "mpesa",
        "timestamp": datetime.now().isoformat()
    }), 200


@mpesa_bp.route("/test", methods=["GET"])
def test_endpoint():
    """Test endpoint."""
    return response(True, {
        "message": "M-Pesa routes are working",
        "timestamp": datetime.now().isoformat()
    })
