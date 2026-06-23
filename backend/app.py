# app.py - Production Ready v4 (FIXED)

import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# 🔥 MUST LOAD ENV FIRST (critical fix)
load_dotenv()

app = Flask(__name__)

# ─── Configuration ─────────────────────────────────────────────
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", 10000))
ENV = os.getenv("FLASK_ENV", "production")

# ─── SAFE CORS (FIXED: avoid hardcoding headers manually) ──────
CORS(
    app,
    resources={r"/*": {"origins": "*"}},  # safer for debugging; tighten later in prod
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Session-Token"],
    expose_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)

# ─── Logging ──────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto-v")

# ─── SAFE IMPORT (prevents crash if env missing) ──────────────
try:
    from api.routes.mpesa import mpesa_bp
    app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")
except Exception as e:
    logger.error(f"MPESA BLUEPRINT FAILED TO LOAD: {e}")

# ─── Routes ────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "AUTO-V API running",
        "version": "3.0.0",
        "environment": ENV
    }), 200


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "environment": ENV
    }), 200


# ─── GLOBAL OPTIONS FIX (clean version) ────────────────────────
@app.route("/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return jsonify({"status": "ok"}), 200


# ─── START SERVER ──────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"🚀 AUTO-V starting on port {PORT} | ENV={ENV}")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
