# api/routes/mpesa.py - Updated with auth

import os
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from services.mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    query_payment_status,
    is_mpesa_configured
)

from services.supabase_client import (
    get_supabase_client,
    get_payment_by_id,
    get_payment_by_custom_id,
    get_payment_by_checkout_id,
    get_payment_by_mpesa_code,
    update_payment,
    get_user_payments
)

# ✅ Add auth middleware
from services.auth_middleware import require_auth, optional_auth, get_current_user

logger = logging.getLogger(__name__)
mpesa_bp = Blueprint("mpesa", __name__)

MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "4095377")
MPESA_ENV = os.getenv("MPESA_ENV", "production")


# ─────────────────────────────────────────────
# RESPONSE WRAPPER
# ─────────────────────────────────────────────

def response(success: bool, data=None, error=None, status=200):
    payload = {"success": success}
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    return jsonify(payload), status


# ─────────────────────────────────────────────
# INITIATE PAYMENT (WITH AUTH)
# ─────────────────────────────────────────────

@mpesa_bp.route("/initiate", methods=["POST", "OPTIONS"])
@require_auth  # ✅ Add authentication
def initiate_payment():
    try:
        if request.method == "OPTIONS":
            return response(True, {"status": "ok"})

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

        # ✅ Get authenticated user
        user = get_current_user()
        user_id = user["user_id"] if user else data.get("user_id")

        payment_id = data.get("payment_id") or f"PAY-{uuid.uuid4().hex[:8].upper()}"
        reference = data.get("reference") or f"AUTO-{uuid.uuid4().hex[:8].upper()}"

        logger.info(f"📤 Payment init: {payment_id} | {phone} | {amount} | user={user_id}")

        result = initiate_stk_push(
            phone=phone,
            amount=amount,
            payment_id=payment_id,
            reference=reference,
            user_id=user_id
        )

        return response(True, {
            "payment_id": payment_id,
            "checkout_request_id": result.get("CheckoutRequestID"),
            "merchant_request_id": result.get("MerchantRequestID")
        })

    except Exception as e:
        logger.error(f"initiate error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)


# ─────────────────────────────────────────────
# STATUS CHECK (WITH OPTIONAL AUTH)
# ─────────────────────────────────────────────

@mpesa_bp.route("/status/<payment_id>", methods=["GET", "OPTIONS"])
@optional_auth  # ✅ Optional auth for public status checks
def get_payment_status(payment_id):
    try:
        if request.method == "OPTIONS":
            return response(True, {"status": "ok"})

        client = get_supabase_client()

        # 1. payment_id lookup
        res = client.table("payments").select("*").eq("payment_id", payment_id).execute()
        if res.data:
            return response(True, res.data[0])

        # 2. checkout id
        payment = get_payment_by_checkout_id(payment_id)
        if payment:
            return response(True, payment)

        # 3. mpesa code
        payment = get_payment_by_mpesa_code(payment_id)
        if payment:
            return response(True, payment)

        # 4. uuid
        try:
            uuid.UUID(payment_id)
            payment = get_payment_by_id(payment_id)
            if payment:
                return response(True, payment)
        except:
            pass

        return response(True, {"status": "not_found"})

    except Exception as e:
        logger.error(e, exc_info=True)
        return response(False, error=str(e), status=500)


# ─────────────────────────────────────────────
# CALLBACK (NO AUTH - M-PESA CALLS THIS)
# ─────────────────────────────────────────────

@mpesa_bp.route("/callback", methods=["POST"])
def mpesa_callback():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"ResultCode": 1, "ResultDesc": "No data"}), 200

        result = handle_mpesa_callback(data)
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"callback error: {e}", exc_info=True)
        return jsonify({"ResultCode": 1, "ResultDesc": "System error"}), 200


# ─────────────────────────────────────────────
# AUTO CONFIRM (FIXED)
# ─────────────────────────────────────────────

@mpesa_bp.route("/auto-confirm/<payment_id>", methods=["POST", "OPTIONS"])
@require_auth  # ✅ Require auth for manual confirmation
def auto_confirm(payment_id):
    try:
        if request.method == "OPTIONS":
            return response(True, {"status": "ok"})

        # ✅ Check if auto_confirm_payment exists, otherwise implement inline
        try:
            from services.mpesa import auto_confirm_payment
            result = auto_confirm_payment(payment_id)
            return response(True, result)
        except ImportError:
            # Fallback: manual confirmation logic
            payment = get_payment_by_custom_id(payment_id)
            if not payment:
                try:
                    uuid.UUID(payment_id)
                    payment = get_payment_by_id(payment_id)
                except:
                    return response(False, error="Payment not found", status=404)
            
            # Update payment status to completed
            update_payment(payment["id"], {"status": "completed"})
            return response(True, {"status": "completed", "payment_id": payment["id"]})

    except Exception as e:
        logger.error(e, exc_info=True)
        return response(False, error=str(e), status=500)


# ─────────────────────────────────────────────
# USER PAYMENTS (WITH AUTH)
# ─────────────────────────────────────────────

@mpesa_bp.route("/user/<user_id>", methods=["GET"])
@require_auth  # ✅ Require auth
def user_payments(user_id):
    try:
        # ✅ Verify user can only see their own payments
        current_user = get_current_user()
        if current_user and current_user["user_id"] != user_id:
            # Allow if admin or same user
            if current_user.get("role") != "admin":
                return response(False, error="Unauthorized", status=403)
        
        limit = request.args.get("limit", 50, type=int)
        payments = get_user_payments(user_id, limit)
        return response(True, {"payments": payments})
    except Exception as e:
        return response(False, error=str(e), status=500)


# ─────────────────────────────────────────────
# HEALTH (PUBLIC)
# ─────────────────────────────────────────────

@mpesa_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "mpesa",
        "environment": MPESA_ENV,
        "shortcode": MPESA_SHORTCODE,
        "configured": is_mpesa_configured()
    })


# ─────────────────────────────────────────────
# TEST (PUBLIC)
# ─────────────────────────────────────────────

@mpesa_bp.route("/test", methods=["GET"])
def test():
    return response(True, {
        "message": "M-Pesa API working",
        "env": MPESA_ENV,
        "shortcode": MPESA_SHORTCODE,
        "configured": is_mpesa_configured()
    })
