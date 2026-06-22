from flask import Flask, jsonify
from flask_cors import CORS
import logging

from api.routes.mpesa import mpesa_bp

app = Flask(__name__)

# ─────────────────────────────────────────────
# STRICT CORS FIX (WORKING FOR MPESA)
# ─────────────────────────────────────────────
CORS(
    app,
    resources={r"/*": {"origins": [
        "https://auto-v.meipressgroup.com"
    ]}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Session-Token"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

logging.basicConfig(level=logging.INFO)

app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")


# ─────────────────────────────────────────────
# FORCE HANDLE PREFLIGHT (VERY IMPORTANT)
# ─────────────────────────────────────────────
@app.route("/", methods=["GET", "OPTIONS"])
def home():
    return jsonify({"status": "AUTO-V API running"}), 200


@app.route("/<path:path>", methods=["OPTIONS"])
def options(path):
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run()
