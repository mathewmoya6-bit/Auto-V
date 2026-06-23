# ============================================================
# CRITICAL SYSTEM FIX - MUST BE FIRST LINE IN APP ENTRYPOINT
# ============================================================

import os

# ─── PROXY HARD RESET (Production Grade) ────────────────────
proxy_keys = [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy"
]

# Remove and override all proxy variables
for k in proxy_keys:
    os.environ.pop(k, None)
    os.environ[k] = ""  # keep override but safer

# HARD GUARANTEE: Prevent HTTPX proxy resolution entirely
os.environ["NO_PROXY"] = "*"  # ✅ Only set once (no redundant setdefault)

# ─── SUPABASE STABILITY FLAGS ──────────────────────────────
# Prevent random timeout crashes with Supabase
os.environ.setdefault("SUPABASE_POSTGREST_CLIENT_TIMEOUT", "60")

# ============================================================
# NOW SAFE TO IMPORT EVERYTHING ELSE
# ============================================================

import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# 🔥 LOAD ENV AFTER PROXY CLEANUP (override=True for Render safety)
load_dotenv(override=True)

app = Flask(__name__)

# ─── Configuration ─────────────────────────────────────────────
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", 10000))
ENV = os.getenv("FLASK_ENV", "production")
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())

# ─── SAFE CORS ──────────────────────────────────────────────
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Session-Token", "Accept"],
    expose_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    max_age=3600
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

# ─── ROOT ROUTES ──────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    """Root endpoint - API information"""
    return jsonify({
        "status": "AUTO-V API running",
        "version": "5.1.0",
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
    """Health check endpoint with proxy verification"""
    # Check proxy status - ✅ Fixed logic
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
    proxy_status = {
        v: "cleared" if os.getenv(v) in (None, "") else os.getenv(v)
        for v in proxy_vars
    }
    
    return jsonify({
        "status": "healthy",
        "environment": ENV,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "services": {
            "mpesa": "configured" if os.getenv("MPESA_CONSUMER_KEY") else "not configured"
        },
        "proxy_status": proxy_status,
        "no_proxy": os.getenv("NO_PROXY", "not set"),
        "supabase_timeout": os.getenv("SUPABASE_POSTGREST_CLIENT_TIMEOUT", "not set")
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

# ─── BEFORE REQUEST ──────────────────────────────────────────
@app.before_request
def before_request():
    """Log all requests in production"""
    if ENV == "production":
        logger.info(f"{request.method} {request.path} - {request.remote_addr}")

# ─── AFTER REQUEST ──────────────────────────────────────────
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
    
    # ✅ Fixed: Better proxy check logic
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
    proxy_set = [v for v in proxy_vars if os.getenv(v) not in (None, "")]
    
    if proxy_set:
        logger.warning(f"⚠️ Proxy variables still set: {proxy_set}")
        logger.warning("   This may cause issues with Supabase/httpx")
    else:
        logger.info("✅ Proxy variables cleared - Supabase/httpx should work correctly")
    
    # Verify NO_PROXY is set
    no_proxy = os.getenv("NO_PROXY")
    if no_proxy == "*":
        logger.info("✅ NO_PROXY='*' set - proxy resolution disabled")
    else:
        logger.warning(f"⚠️ NO_PROXY='{no_proxy}' - may not fully disable proxy")
        logger.warning("   ⚠️ Set NO_PROXY='*' in Render environment variables")
    
    # Verify Supabase timeout
    timeout = os.getenv("SUPABASE_POSTGREST_CLIENT_TIMEOUT")
    if timeout:
        logger.info(f"✅ Supabase timeout set to {timeout}s")
    
    # 🚀 Render environment recommendation
    logger.info("")
    logger.info("📋 For production, add these to Render environment:")
    logger.info("   NO_PROXY=*")
    logger.info("   HTTP_PROXY=")
    logger.info("   HTTPS_PROXY=")
    logger.info("")
    
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
