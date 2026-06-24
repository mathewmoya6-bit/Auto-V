# ============================================================
# api/webhooks.py - Webhook Routes
# ============================================================

import os
import logging
from flask import Blueprint, request, jsonify

from services.mpesa import handle_mpesa_callback

logger = logging.getLogger(__name__)

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")


@webhooks_bp.route("/mpesa", methods=["POST"])
def mpesa_webhook():
    """Handle M-Pesa webhook callbacks."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400

        logger.info(f"Webhook received: {data}")

        result = handle_mpesa_callback(data)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@webhooks_bp.route("/health", methods=["GET"])
def health():
    """Health check for webhooks."""
    return jsonify({"status": "ok", "service": "webhooks"}), 200
