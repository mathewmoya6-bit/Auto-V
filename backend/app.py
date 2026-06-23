# app.py - Production Ready v5 (FULLY ALIGNED)

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
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())  # For sessions if needed

# ─── SAFE CORS (FIXED: avoid hardcoding headers manually) ──────
CORS(
    app,
    resources={r"/*": {"origins": "*"}},  # safer for debugging; tighten later in prod
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Session-Token", "Accept"],
    expose_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    max_age=3600  # Cache preflight requests for 1 hour
)

# ─── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auto-v")

# ─── BLUEPRINT REGISTRATION ──────────────────────────────────
try:
    from api.routes.mpesa import mpesa_bp
    app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")
    logger.info("✅ M-Pesa blueprint registered successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import M-Pesa blueprint: {e}")
    logger.error("   Make sure api/routes/mpesa.py exists")
except Exception as e:
    logger.error(f"❌ M-Pesa blueprint failed to load: {e}")

# Try to load any additional blueprints
try:
    # Placeholder for future blueprints (auth, admin, etc.)
    # from api.routes.auth import auth_bp
    # app.register_blueprint(auth_bp, url_prefix="/api/auth")
    pass
except Exception as e:
    logger.warning(f"Additional blueprints not loaded: {e}")

# ─── ROOT ROUTES ──────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    """Root endpoint - API information"""
    return jsonify({
        "status": "AUTO-V API running",
        "version": "3.0.0",
        "environment": ENV,
        "services": {
            "mpesa": "loaded" if "mpesa_bp" in locals() else "failed"
        },
        "endpoints": {
            "health": "/api/health",
            "mpesa": "/api/mpesa/health",
            "mpesa_test": "/api/mpesa/test"
        }
    }), 200

@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "environment": ENV,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "services": {
            "mpesa": "configured" if os.getenv("MPESA_CONSUMER_KEY") else "not configured"
        }
    }), 200

# ─── GLOBAL OPTIONS HANDLER ──────────────────────────────────
@app.route("/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    """Handle preflight OPTIONS requests globally"""
    return jsonify({"status": "ok"}), 200

# ─── ERROR HANDLERS ──────────────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Not Found",
        "message": "The requested resource was not found"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred"
    }), 500

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        "error": "Method Not Allowed",
        "message": "The HTTP method is not allowed for this endpoint"
    }), 405

# ─── BEFORE REQUEST (Optional) ──────────────────────────────
@app.before_request
def before_request():
    """Log all requests in production"""
    if ENV == "production":
        logger.info(f"{request.method} {request.path} - {request.remote_addr}")

# ─── AFTER REQUEST (Optional) ──────────────────────────────
@app.after_request
def after_request(response):
    """Add security headers to all responses"""
    response.headers.add('X-Content-Type-Options', 'nosniff')
    response.headers.add('X-Frame-Options', 'DENY')
    response.headers.add('X-XSS-Protection', '1; mode=block')
    return response

# ─── START SERVER ──────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"🚀 AUTO-V starting on port {PORT} | ENV={ENV}")
    logger.info(f"📍 Health check: http://localhost:{PORT}/api/health")
    logger.info(f"📍 M-Pesa test: http://localhost:{PORT}/api/mpesa/test")
    
    # Check if M-Pesa is configured
    if not os.getenv("MPESA_CONSUMER_KEY"):
        logger.warning("⚠️ M-Pesa environment variables not fully configured")
        logger.warning("   Set MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET, MPESA_PASSKEY")
    
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
