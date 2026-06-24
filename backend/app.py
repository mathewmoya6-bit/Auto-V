# ============================================================
# AUTO-V API - CORRECT IMPORT ORDER
# ============================================================

# ─── Step 1: Load environment variables FIRST ──────────────
import os
import logging
from dotenv import load_dotenv

# Load .env before ANY other imports
load_dotenv()

# ─── Step 2: Now import everything else ────────────────────
from flask import Flask, jsonify, request
from flask_cors import CORS

from api.routes.mpesa import mpesa_bp

# ─── Step 3: Create the app ────────────────────────────────
app = Flask(__name__)

# ─── Step 4: Configure CORS ────────────────────────────────
CORS(app, resources={r"/*": {"origins": "*"}})

# ─── Step 5: Register Blueprints ────────────────────────────
app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")

# ─── Step 6: Routes ──────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "success": True,
        "data": {
            "name": "AUTO-V API",
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "status": "operational"
        }
    })

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "success": True,
        "data": {
            "status": "healthy",
            "environment": os.getenv("FLASK_ENV", "production"),
            "supabase_url": os.getenv("SUPABASE_URL", "not set")
        }
    })

# ─── Step 7: Run ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
