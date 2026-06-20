# app.py - Enterprise-Grade Flask Application (CORS FULLY HARDENED)

import os
import sys
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

# ─── Initialize Flask App ─────────────────────────────────────
app = Flask(__name__)

# ─── Logging ──────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info(f"📋 Log level set to: {LOG_LEVEL}")

# ─── Debug: Show file structure ──────────────────────────────
logger.info(f"📁 Current directory: {os.getcwd()}")
try:
    logger.info(f"📁 Files: {os.listdir('.')}")
except:
    pass

# ─── Environment Variables ──────────────────────────────────
REQUIRED_ENV_VARS = {
    'MPESA_CONSUMER_KEY': 'M-Pesa Consumer Key',
    'MPESA_CONSUMER_SECRET': 'M-Pesa Consumer Secret',
    'MPESA_PASSKEY': 'M-Pesa Passkey',
    'MPESA_SHORTCODE': 'M-Pesa Shortcode',
    'MPESA_CALLBACK_URL': 'M-Pesa Callback URL',
    'SUPABASE_URL': 'Supabase URL',
    'SUPABASE_ANON_KEY': 'Supabase Anon Key'
}

MISSING_ENV_VARS = []
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        MISSING_ENV_VARS.append(var)

if MISSING_ENV_VARS:
    logger.warning(f"⚠️ Missing: {', '.join(MISSING_ENV_VARS)}")
else:
    logger.info("✅ All environment variables set")

# ─── =========================================================───
# ─── CORS SYSTEM - FULLY HARDENED ──────────────────────────────
# ─── =========================================================───

ALLOWED_ORIGINS = [
    "https://auto-v.meipressgroup.com",
    "https://auto-v.onrender.com",
    "http://localhost:3000",
    "http://localhost:5000"
]

# ✅ Primary CORS via Flask-CORS
CORS(app, 
     resources={r"/api/*": {
         "origins": ALLOWED_ORIGINS,
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
         "allow_headers": [
             "Content-Type",
             "Authorization",
             "Accept",
             "X-Requested-With"
         ],
         "expose_headers": ["Content-Type", "Authorization"],
         "supports_credentials": True,
         "max_age": 86400
     }},
    supports_credentials=True
)

# ✅ Preflight handler - FULL response
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept"
            response.headers["Access-Control-Max-Age"] = "86400"
        return response, 204

# ✅ Backup CORS headers on EVERY response
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin and origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept"
        response.headers["Access-Control-Expose-Headers"] = "Content-Type, Authorization"
    return response


# ─── =========================================================───
# ─── RATE LIMITER ───────────────────────────────────────────────
# ─── =========================================================───

REDIS_URL = os.getenv('REDIS_URL', None)

if REDIS_URL and REDIS_URL.startswith("redis"):
    storage_uri = REDIS_URL
    logger.info(f"✅ Using Redis for rate limiting")
else:
    storage_uri = "memory://"
    logger.warning("⚠️ Using memory for rate limiting")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per hour", "100 per minute"],
    storage_uri=storage_uri,
    swallow_errors=True
)
limiter.init_app(app)
logger.info("✅ Rate limiter initialized")


# ─── =========================================================───
# ─── ROUTES ──────────────────────────────────────────────────────
# ─── =========================================================───

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'mpesa_loaded': mpesa_loaded
    }), 200

@app.route('/api/ping', methods=['GET', 'OPTIONS'])
def ping():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify({'status': 'ok', 'message': 'pong'}), 200


# ─── =========================================================───
# ─── BLUEPRINT REGISTRATION ─────────────────────────────────────
# ─── =========================================================───

mpesa_loaded = False

def register_blueprints():
    global mpesa_loaded
    
    # Try all possible paths
    paths = [
        'backend.api.routes.mpesa',
        'api.routes.mpesa',
        'routes.mpesa',
        'backend.routes.mpesa',
        'api.mpesa'
    ]
    
    sys.path.insert(0, os.getcwd())
    
    for path in paths:
        try:
            logger.info(f"🔍 Trying: {path}")
            module = __import__(path, fromlist=['mpesa_bp'])
            if hasattr(module, 'mpesa_bp'):
                bp = getattr(module, 'mpesa_bp')
                app.register_blueprint(bp, url_prefix='/api/mpesa')
                mpesa_loaded = True
                logger.info(f"✅ Registered from: {path}")
                return
        except Exception as e:
            logger.warning(f"⚠️ Failed: {path} - {e}")
    
    logger.critical("❌ No mpesa blueprint found!")

register_blueprints()


# ─── =========================================================───
# ─── ERROR HANDLERS ──────────────────────────────────────────────
# ─── =========================================================───

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found', 'path': request.path}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"500: {request.path}", exc_info=True)
    return jsonify({'error': 'Internal error'}), 500

@app.errorhandler(429)
def rate_limit_error(e):
    return jsonify({'error': 'Too many requests'}), 429


# ─── =========================================================───
# ─── MAIN ────────────────────────────────────────────────────────
# ─── =========================================================───

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    logger.info(f"🚀 Starting on port {port}")
    logger.info(f"✅ M-Pesa loaded: {mpesa_loaded}")
    app.run(host='0.0.0.0', port=port, debug=False)
