# app.py - Enterprise-Grade Flask Application (CORS FIXED FINAL)

import os
import sys
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# ─── Load Environment ──────────────────────────────────────────
load_dotenv()

# ─── Initialize Flask App ─────────────────────────────────────
app = Flask(__name__)

# ─── Logging Configuration ────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info(f"📋 Log level set to: {LOG_LEVEL}")

# ─── Debug: Show current directory ────────────────────────────
logger.info(f"📁 Current working directory: {os.getcwd()}")
try:
    logger.info(f"📁 Contents: {os.listdir('.')}")
except Exception as e:
    logger.warning(f"⚠️ Could not list directory: {e}")


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

def validate_environment():
    global MISSING_ENV_VARS
    missing = []
    for var, description in REQUIRED_ENV_VARS.items():
        if not os.getenv(var):
            missing.append(f"{var} ({description})")
    MISSING_ENV_VARS = missing
    if missing:
        logger.warning(f"⚠️ Missing environment variables: {', '.join(missing)}")
    else:
        logger.info("✅ All required environment variables are set")
    return missing

validate_environment()


# ─── =========================================================───
# ─── CORS SYSTEM - BULLETPROOF ─────────────────────────────────
# ─── =========================================================───

ALLOWED_ORIGINS = [
    "https://auto-v.meipressgroup.com",
    "https://auto-v.onrender.com",
    "http://localhost:3000",
    "http://localhost:5000"
]

# ✅ ONLY use Flask-CORS (remove manual after_request)
CORS(app, 
     resources={r"/api/*": {
         "origins": ALLOWED_ORIGINS,
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
         "allow_headers": [
             "Content-Type",
             "Authorization",
             "Accept",
             "X-Requested-With",
             "X-CSRFToken"
         ],
         "expose_headers": [
             "Content-Type",
             "Authorization",
             "X-Total-Count"
         ],
         "supports_credentials": True,
         "max_age": 86400
     }},
    supports_credentials=True
)

# ✅ FIXED: Global preflight handler using Flask's default
@app.before_request
def handle_preflight():
    """Handle OPTIONS requests globally."""
    if request.method == "OPTIONS":
        # Let Flask-CORS handle headers automatically
        return app.make_default_options_response()


# ─── =========================================================───
# ─── RATE LIMITER ───────────────────────────────────────────────
# ─── =========================================================───

REDIS_URL = os.getenv('REDIS_URL', None)

if REDIS_URL and (REDIS_URL.startswith("redis://") or REDIS_URL.startswith("rediss://")):
    storage_uri = REDIS_URL
    logger.info(f"✅ Using Redis for rate limiting: {REDIS_URL[:30]}...")
else:
    storage_uri = "memory://"
    logger.warning("⚠️ Using memory for rate limiting (not production-safe)")

# ✅ FIXED: Added swallow_errors to prevent limiter from breaking OPTIONS
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per hour", "100 per minute"],
    storage_uri=storage_uri,
    swallow_errors=True
)
limiter.init_app(app)
logger.info("✅ Rate limiter initialized successfully")


# ─── =========================================================───
# ─── SECURITY MIDDLEWARE ────────────────────────────────────────
# ─── =========================================================───

app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB


# ─── =========================================================───
# ─── ROUTES ──────────────────────────────────────────────────────
# ─── =========================================================───

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'environment': os.getenv('FLASK_ENV', 'production'),
        'redis_connected': bool(REDIS_URL),
        'mpesa_configured': all([os.getenv(v) for v in REQUIRED_ENV_VARS.keys()])
    }), 200

@app.route('/api/test', methods=['GET'])
def test_route():
    return jsonify({
        'status': 'ok',
        'message': 'API is working',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200


# ─── =========================================================───
# ─── REGISTER BLUEPRINTS ────────────────────────────────────────
# ─── =========================================================───

mpesa_loaded = False

def register_blueprints():
    global mpesa_loaded
    
    sys.path.insert(0, os.getcwd())
    
    import_paths = [
        'backend.api.routes.mpesa',
        'api.routes.mpesa',
        'routes.mpesa',
        'backend.routes.mpesa'
    ]
    
    for import_path in import_paths:
        try:
            logger.info(f"🔍 Trying to import: {import_path}")
            module = __import__(import_path, fromlist=['mpesa_bp'])
            if hasattr(module, 'mpesa_bp'):
                mpesa_bp = getattr(module, 'mpesa_bp')
                app.register_blueprint(mpesa_bp, url_prefix='/api/mpesa')
                mpesa_loaded = True
                logger.info(f"✅ M-Pesa routes registered from: {import_path}")
                return
        except ImportError as e:
            logger.warning(f"⚠️ Import failed from {import_path}: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Error from {import_path}: {e}")
    
    logger.critical("❌ CRITICAL: Could not import mpesa blueprint from any path!")

register_blueprints()


# ─── =========================================================───
# ─── ERROR HANDLERS ──────────────────────────────────────────────
# ─── =========================================================───

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found', 'path': request.path}), 404

@app.errorhandler(413)
def request_too_large(error):
    return jsonify({'error': 'Request too large. Maximum size is 10MB'}), 413

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500: {request.path}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def rate_limit_error(error):
    return jsonify({
        'error': 'Too many requests. Please try again later.',
        'retry_after': 60
    }), 429


# ─── =========================================================───
# ─── APPLICATION FACTORY ────────────────────────────────────────
# ─── =========================================================───

def create_app():
    logger.info("=" * 60)
    logger.info("🚀 AUTO-V Backend Started")
    logger.info(f"📡 Environment: {os.getenv('FLASK_ENV', 'production')}")
    logger.info(f"📡 Port: {os.getenv('PORT', 10000)}")
    logger.info(f"✅ Payment system loaded: {mpesa_loaded}")
    logger.info("=" * 60)
    return app


# ─── Main Entry Point ─────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development')
