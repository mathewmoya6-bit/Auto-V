# ============================================================
# AUTO-V API - FIXED IMPORT
# ============================================================

import os
import sys
import logging
from dotenv import load_dotenv

# Add current directory to path so Python can find modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from flask import Flask, jsonify, request
from flask_cors import CORS

# Import using absolute path
from api.routes.mpesa import mpesa_bp

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

# Register Blueprints
app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")

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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
