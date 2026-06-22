# api/routes/mpesa.py - M-Pesa API Routes (Production Ready v2)

import os
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

from services.mpesa import (
    initiate_stk_push,
    handle_mpesa_callback,
    query_payment_status,
    verify_payment_with_mpesa,
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
    get_user_payments,
    get_payment_stats
)

logger = logging.getLogger(__name__)

mpesa_bp = Blueprint('mpesa', __name__)

# ─── CONFIG ──────────────────────────────────────────────
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
MPESA_ENV = os.getenv('MPESA_ENV', 'production')


# ─── RESPONSE HELPER ─────────────────────────────────────
def standard_response(success: bool, data=None, error=None, status=200):
    return jsonify({
        "success": success,
        "data": data,
        "error": error
    }), status


# ──────────────────────────────────────────────────────────
# INITIATE PAYMENT
# ──────────────────────────────────────────────────────────
@mpesa_bp.route('/initiate', methods=['POST'])
def initiate_payment():
    try:
        data = request.get_json()

        if not data:
            return standard_response(False, error="No data provided", status=400)

        required = ['phone', 'amount']
        missing = [f for f in required if not data.get(f)]

        if missing:
            return standard_response(False, error=f"Missing: {missing}", status=400)

        payment_id = data.get('payment_id') or f"PAY-{uuid.uuid4().hex[:8].upper()}"
        reference = data.get('reference') or f"AUTO-{uuid.uuid4().hex[:8].upper()}"

        phone = data['phone']
        amount = float(str(data['amount']).replace(",", ""))

        if amount <= 0:
            return standard_response(False, error="Invalid amount", status=400)

        result = initiate_stk_push(
            phone=phone,
            amount=amount,
            payment_id=payment_id,
            service=data.get('service', 'AUTO-V'),
            reference=reference,
            user_id=data.get('user_id'),
            request_id=data.get('request_id')
        )

        return standard_response(True, data={
            "payment_id": payment_id,
            "checkout_request_id": result.get("checkout_request_id"),
            "merchant_request_id": result.get("merchant_request_id"),
            "reference": reference
        })

    except Exception as e:
        logger.error(f"initiate error: {e}", exc_info=True)
        return standard_response(False, error="Payment failed", status=500)


# ──────────────────────────────────────────────────────────
# STATUS (FIXED: payment TABLE ONLY)
# ──────────────────────────────────────────────────────────
@mpesa_bp.route('/status/<payment_id>', methods=['GET'])
def get_payment_status(payment_id):
    try:
        supabase = get_supabase_client()

        # 1. payment_id (primary business ID)
        response = supabase.table('payment') \
            .select('*') \
            .eq('payment_id', payment_id) \
            .execute()

        payment = response.data[0] if response.data else None

        # 2. checkout_request_id
        if not payment:
            payment = get_payment_by_checkout_id(payment_id)

        # 3. mpesa_code
        if not payment:
            payment = get_payment_by_mpesa_code(payment_id)

        # 4. UUID fallback
        if not payment:
            try:
                uuid.UUID(payment_id)
                payment = get_payment_by_id(payment_id)
            except:
                pass

        if not payment:
            return standard_response(True, data={
                "payment_id": payment_id,
                "status": "not_found"
            })

        return standard_response(True, data={
            "payment_id": payment.get("payment_id"),
            "id": payment.get("id"),
            "status": payment.get("status"),
            "amount": payment.get("amount"),
            "checkout_request_id": payment.get("checkout_request_id"),
            "mpesa_code": payment.get("mpesa_code"),
            "paid_at": payment.get("paid_at"),
            "created_at": payment.get("created_at")
        })

    except Exception as e:
        logger.error(f"status error: {e}", exc_info=True)
        return standard_response(False, error="Status failed", status=500)


# ──────────────────────────────────────────────────────────
# VERIFY PAYMENT
# ──────────────────────────────────────────────────────────
@mpesa_bp.route('/verify/<checkout_id>', methods=['POST'])
def verify_payment(checkout_id):
    try:
        result = verify_payment_with_mpesa(checkout_id)

        return standard_response(True, data=result)

    except Exception as e:
        return standard_response(False, error="Verify failed", status=500)


# ──────────────────────────────────────────────────────────
# CALLBACK (SAFE FOR SAFARICOM)
# ──────────────────────────────────────────────────────────
@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback_route():
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"ResultCode": 1, "ResultDesc": "No data"}), 200

        result = handle_mpesa_callback(data)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"callback error: {e}", exc_info=True)
        return jsonify({"ResultCode": 1, "ResultDesc": "System error"}), 200


# ──────────────────────────────────────────────────────────
# AUTO CONFIRM
# ──────────────────────────────────────────────────────────
@mpesa_bp.route('/auto-confirm/<payment_id>', methods=['POST'])
def auto_confirm(payment_id):
    try:
        payment = get_payment_by_custom_id(payment_id)

        if not payment:
            try:
                uuid.UUID(payment_id)
                payment = get_payment_by_id(payment_id)
            except:
                pass

        if not payment:
            return standard_response(False, error="Not found", status=404)

        result = auto_confirm_payment(payment["id"])

        return standard_response(True, data=result)

    except Exception as e:
        return standard_response(False, error="Auto confirm failed", status=500)


# ──────────────────────────────────────────────────────────
# USER PAYMENTS
# ──────────────────────────────────────────────────────────
@mpesa_bp.route('/user/<user_id>', methods=['GET'])
def user_payments(user_id):
    try:
        limit = request.args.get("limit", 50)
        data = get_user_payments(user_id, limit)

        return standard_response(True, data={
            "payments": data,
            "count": len(data)
        })

    except Exception as e:
        return standard_response(False, error="Failed", status=500)


# ──────────────────────────────────────────────────────────
# STATS
# ──────────────────────────────────────────────────────────
@mpesa_bp.route('/stats', methods=['GET'])
def stats():
    try:
        return standard_response(True, data=get_payment_stats())
    except Exception:
        return standard_response(False, error="Failed", status=500)


# ──────────────────────────────────────────────────────────
# HEALTH
# ──────────────────────────────────────────────────────────
@mpesa_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        "service": "mpesa",
        "status": "healthy",
        "configured": is_mpesa_configured(),
        "shortcode": MPESA_SHORTCODE
    }), 200
