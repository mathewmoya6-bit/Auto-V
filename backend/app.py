from flask import Flask, jsonify
from flask_cors import CORS
import logging

from api.routes.mpesa import mpesa_bp

app = Flask(__name__)

# ─────────────────────────────────────────────
# CORS FIX (CRITICAL FOR FRONTEND FETCH)
# ─────────────────────────────────────────────
CORS(
    app,
    resources={r"/*": {"origins": [
        "https://auto-v.meipressgroup.com",
        "http://localhost:3000",
        "http://127.0.0.1:5500"
    ]}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Session-Token"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

logging.basicConfig(level=logging.INFO)

# register routes
app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")


@app.route("/")
def home():
    return jsonify({"status": "AUTO-V API running"})


# ─────────────────────────────────────────────
# GLOBAL OPTIONS HANDLER (FIX PREFLIGHT FAIL)
# ─────────────────────────────────────────────
@app.route("/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return jsonify({}), 200


if __name__ == "__main__":
    app.run(debug=True)
