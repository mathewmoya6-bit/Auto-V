# ============================================================
# api/routes/mpesa.py - Production Ready v8 (FIXED)
# ============================================================

import os
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

# ─── Service Imports ──────────────────────────────────────
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
    get_payment_by_checkout_id,
    get_payment_by_mpesa_code,
    update_payment,
    update_payment_by_custom_id,
    get_user_payments
)

# ─── Logger ───────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ─── Blueprint (NO url_prefix here - set in app registration) ──
mpesa_bp = Blueprint("mpesa", __name__)

# ─── Config ───────────────────────────────────────────────
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "4095377")
MPESA_ENV = os.getenv("MPESA_ENV", "production").lower().strip()


# ──────────────────────────────────────────────────────────
# RESPONSE WRAPPER (with CORS headers)
# ──────────────────────────────────────────────────────────

def response(success: bool, data=None, error=None, status=200):
    """Standard API response wrapper with CORS headers."""
    payload = {"success": success}
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    
    resp = jsonify(payload)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    
    return resp, status


# ──────────────────────────────────────────────────────────
# HELPER: Get Payment by Custom ID
# ──────────────────────────────────────────────────────────

def get_payment_by_custom_id(payment_id):
    """Get payment by any ID format (payment_id, checkout_id, mpesa_code)."""
    try:
        client = get_supabase_client()
        
        # Try as payment_id
        result = client.table("payments").select("*").eq("payment_id", payment_id).execute()
        if result.data:
            return result.data[0]
        
        # Try as checkout_request_id
        result = client.table("payments").select("*").eq("checkout_request_id", payment_id).execute()
        if result.data:
            return result.data[0]
        
        # Try as mpesa_code
        result = client.table("payments").select("*").eq("mpesa_code", payment_id).execute()
        if result.data:
            return result.data[0]
        
        # Try as UUID
        try:
            uuid.UUID(payment_id)
            result = client.table("payments").select("*").eq("id", payment_id).execute()
            if result.data:
                return result.data[0]
        except:
            pass
        
        return None
    except Exception as e:
        logger.error(f"get_payment_by_custom_id error: {e}")
        return None


# ──────────────────────────────────────────────────────────
# ROUTE: Initiate STK Push (FIXED - explicit methods)
# ──────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────
# ROUTE: Get Payment Status
# ──────────────────────────────────────────────────────────

@mpesa_bp.route("/status/<payment_id>", methods=["GET", "OPTIONS"])
def get_payment_status(payment_id):
    """Get payment status by ID."""
    try:
        if request.method == "OPTIONS":
            return response(True, {"status": "ok"})

        payment = get_payment_by_custom_id(payment_id)
        
        if payment:
            return response(True, payment)

        return response(True, {"status": "not_found"})

    except Exception as e:
        logger.error(e, exc_info=True)
        return response(False, error=str(e), status=500)


# ──────────────────────────────────────────────────────────
# ROUTE: M-Pesa Callback
# ──────────────────────────────────────────────────────────

@mpesa_bp.route("/callback", methods=["POST"])
def mpesa_callback():
    """Handle M-Pesa callback from Safaricom."""
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
# ROUTE: Auto-Confirm Payment
# ──────────────────────────────────────────────────────────

@mpesa_bp.route("/auto-confirm/<payment_id>", methods=["POST", "OPTIONS"])
def auto_confirm(payment_id):
    """Auto-confirm a pending payment."""
    try:
        if request.method == "OPTIONS":
            return response(True, {"status": "ok"})

        payment = get_payment_by_custom_id(payment_id)

        if not payment:
            return response(False, error="Payment not found", status=404)

        result = auto_confirm_payment(payment["id"])

        return response(True, result)

    except Exception as e:
        logger.error(e, exc_info=True)
        return response(False, error=str(e), status=500)


# ──────────────────────────────────────────────────────────
# ROUTE: Get User Payments
# ──────────────────────────────────────────────────────────

@mpesa_bp.route("/user/<user_id>", methods=["GET"])
def user_payments(user_id):
    """Get all payments for a user."""
    try:
        limit = request.args.get("limit", 50, type=int)
        payments = get_user_payments(user_id, limit)
        return response(True, {"payments": payments})
    except Exception as e:
        return response(False, error=str(e), status=500)


# ──────────────────────────────────────────────────────────
# ROUTE: Query Payment Status (from Safaricom)
# ──────────────────────────────────────────────────────────

@mpesa_bp.route("/query/<checkout_request_id>", methods=["GET"])
def query_status(checkout_request_id):
    """Query payment status from Safaricom."""
    try:
        result = query_payment_status(checkout_request_id)
        return response(True, result)
    except Exception as e:
        logger.error(f"query error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)


# ──────────────────────────────────────────────────────────
# ROUTE: Health Check
# ──────────────────────────────────────────────────────────

@mpesa_bp.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "mpesa",
        "environment": MPESA_ENV,
        "shortcode": MPESA_SHORTCODE,
        "configured": is_mpesa_configured(),
        "timestamp": datetime.utcnow().isoformat(),
        "routes_available": [
            "POST /api/mpesa/initiate",
            "GET /api/mpesa/status/<id>",
            "POST /api/mpesa/callback",
            "POST /api/mpesa/auto-confirm/<id>",
            "GET /api/mpesa/user/<user_id>",
            "GET /api/mpesa/query/<checkout_id>",
            "GET /api/mpesa/health",
            "GET /api/mpesa/test"
        ]
    })


# ──────────────────────────────────────────────────────────
# ROUTE: Test Endpoint
# ──────────────────────────────────────────────────────────

@mpesa_bp.route("/test", methods=["GET"])
def test():
    """Test endpoint to verify M-Pesa API is working."""
    return response(True, {
        "message": "M-Pesa API working",
        "env": MPESA_ENV,
        "shortcode": MPESA_SHORTCODE,
        "configured": is_mpesa_configured(),
        "routes_registered": True
    })


# ──────────────────────────────────────────────────────────
# ROUTE: Debug Routes
# ──────────────────────────────────────────────────────────

@mpesa_bp.route("/routes", methods=["GET"])
def list_routes():
    """Debug: List all registered M-Pesa routes."""
    routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint.startswith("mpesa"):
            routes.append({
                "endpoint": rule.endpoint,
                "methods": list(rule.methods),
                "path": str(rule),
                "full_url": f"/api/mpesa{str(rule)}"
            })
    
    return jsonify({
        "routes": routes,
        "total": len(routes),
        "blueprint": "mpesa",
        "base_url": "/api/mpesa",
        "expected_prefix": "/api/mpesa"
    }), 200


# ──────────────────────────────────────────────────────────
# ROUTE: Webhook for External Systems
# ──────────────────────────────────────────────────────────

@mpesa_bp.route("/webhook", methods=["POST"])
def webhook():
    """Webhook endpoint for external systems to notify payment."""
    try:
        data = request.get_json()
        if not data:
            return response(False, error="No data", status=400)
        
        payment_id = data.get("payment_id")
        status = data.get("status")
        
        if not payment_id or not status:
            return response(False, error="payment_id and status required", status=400)
        
        updated = update_payment_by_custom_id(payment_id, {"status": status})
        
        if updated:
            return response(True, {"message": "Webhook processed"})
        else:
            return response(False, error="Payment not found", status=404)
            
    except Exception as e:
        logger.error(f"webhook error: {e}", exc_info=True)
        return response(False, error=str(e), status=500)
