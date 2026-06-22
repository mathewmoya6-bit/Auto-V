from flask import Flask, jsonify, request
from flask_cors import CORS
import logging

from api.routes.mpesa import mpesa_bp

app = Flask(__name__)

# ─────────────────────────────────────────────
# COMPLETE CORS CONFIGURATION
# ─────────────────────────────────────────────
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
    max_age=3600  # Cache preflight for 1 hour
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# REGISTER BLUEPRINTS
# ─────────────────────────────────────────────
app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")


# ─────────────────────────────────────────────
# GLOBAL PREFLIGHT HANDLER
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# ROOT ROUTE
# ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "AUTO-V API running",
        "service": "mpesa",
        "version": "1.0.0"
    }), 200


# ─────────────────────────────────────────────
# CATCH-ALL FOR PREFLIGHT
# ─────────────────────────────────────────────
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
    app.run(host="0.0.0.0", port=10000, debug=False)
