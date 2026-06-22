from flask import Flask, jsonify
from flask_cors import CORS
import logging

from api.routes.mpesa import mpesa_bp

# ─── App Init ─────────────────────────────────────────────
app = Flask(__name__)

# ─── Logging ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)

# ─── CORS FIX (CRITICAL) ───────────────────────────────────
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://auto-v.meipressgroup.com",
            "https://auto-v.onrender.com",
            "http://localhost:5500",
            "http://127.0.0.1:5500"
        ]
    }
})

# ─── Blueprints ────────────────────────────────────────────
app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")


# ─── Health Route ──────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "status": "AUTO-V API running",
        "environment": "production"
    })


# ─── GLOBAL CORS SAFETY (handles preflight OPTIONS) ────────
@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "https://auto-v.meipressgroup.com"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response


# ─── Run Locally ───────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
