# app.py - Production Ready v3

import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from api.routes.mpesa import mpesa_bp

load_dotenv()

app = Flask(__name__)

# ─── Configuration ─────────────────────────────────────────────
DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
PORT = int(os.getenv('PORT', 10000))
ENV = os.getenv('FLASK_ENV', 'production')

# ─── CORS Configuration ────────────────────────────────────────
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "https://auto-v.meipressgroup.com",
                "https://auto-v.onrender.com",
                "http://localhost:3000",
                "http://localhost:5000"
            ]
        }
    },
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Session-Token", "Accept"],
    expose_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    max_age=3600
)

# ─── Logging ──────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Preflight Handler ─────────────────────────────────────────
@app.before_request
def handle_preflight():
    """Handle OPTIONS requests globally."""
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "https://auto-v.meipressgroup.com")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session-Token")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        response.headers.add("Access-Control-Max-Age", "3600")
        return response, 200

# ─── Register Blueprints ──────────────────────────────────────
app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")

# ─── Routes ────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "AUTO-V API running",
        "service": "mpesa",
        "version": "3.0.0",
        "environment": ENV
    }), 200

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "environment": ENV,
        "timestamp": "2026-06-22T17:00:00Z"
    }), 200

@app.route("/<path:path>", methods=["OPTIONS"])
def catch_all_options(path):
    response = jsonify({"status": "ok"})
    response.headers.add("Access-Control-Allow-Origin", "https://auto-v.meipressgroup.com")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session-Token")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Max-Age", "3600")
    return response, 200

if __name__ == "__main__":
    logger.info(f"🚀 Starting AUTO-V API on port {PORT} (ENV: {ENV})")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
