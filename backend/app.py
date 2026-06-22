# app.py - AUTO-V Production Entry Point

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

from api import register_blueprints

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ─── CORS (PRODUCTION SAFE) ─────────────────────────────
CORS(
    app,
    resources={r"/api/*": {"origins": [
        "https://auto-v.meipressgroup.com"
    ]}},
    supports_credentials=True
)

# ─── HEALTH CHECK ───────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "status": "AUTO-V API RUNNING",
        "version": "1.0.0"
    })

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

# ─── REGISTER ROUTES ────────────────────────────────────
register_blueprints(app)

# ─── RUN ────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
