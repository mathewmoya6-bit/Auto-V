# app.py - Complete Hardened Flask Application (FINAL)

import os
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

# ─── Environment Variables (Validated Once at Startup) ──────
REQUIRED_ENV_VARS = [
    'MPESA_CONSUMER_KEY',
    'MPESA_CONSUMER_SECRET',
    'MPESA_PASSKEY',
    'MPESA_SHORTCODE',
    'MPESA_CALLBACK_URL',
    'SUPABASE_URL',
    'SUPABASE_ANON_KEY'
]

MISSING_ENV_VARS = []

def validate_environment():
    """Validate required environment variables (called once at startup)."""
    global MISSING_ENV_VARS
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing.append(var)
    
    MISSING_ENV_VARS = missing
    
    if missing:
        logger.warning(f"⚠️ Missing environment variables: {', '.join(missing)}")
        logger.warning("⚠️ Some features may not work correctly")
    else:
        logger.info("✅ All required environment variables are set")
    
    return missing

# ─── Run validation ONCE at startup ──────────────────────────
validate_environment()


# ─── CORS Configuration (HARDENED) ────────────────────────────
CORS(app, 
     resources={r"/api/*": {
         "origins": [
             "https://auto-v.meipressgroup.com",
             "https://auto-v.onrender.com",
             "http://localhost:3000",
             "http://localhost:5000"
         ],
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization", "Accept"],
         "expose_headers": ["Content-Type", "Authorization"],
         "supports_credentials": True,
         "max_age": 3600
     }}
)


# ─── Rate Limiter Configuration (PRODUCTION) ──────────────────
REDIS_URL = os.getenv('REDIS_URL', None)

# ✅ Validate Redis URL format
if REDIS_URL and REDIS_URL.startswith("redis"):
    storage_uri = REDIS_URL
    logger.info(f"✅ Using Redis for rate limiting: {REDIS_URL[:30]}...")
else:
    storage_uri = "memory://"
    if REDIS_URL:
        logger.warning(f"⚠️ Invalid Redis URL format: {REDIS_URL}. Using memory storage.")
    else:
        logger.warning("⚠️ Using memory for rate limiting (not production-safe)")

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["500 per hour", "100 per minute"],
    storage_uri=storage_uri,
    strategy="fixed-window"
)


# ─── Request Logging Middleware (DEV ONLY) ────────────────────
if os.getenv("FLASK_ENV") == "development":
    @app.before_request
    def log_request():
        """Log all incoming requests (development only)."""
        logger.debug(f"→ {request.method} {request.path} - {request.remote_addr}")
        
        # Only log request body for payment endpoints in debug mode
        if request.path.startswith('/api/mpesa') and request.method in ['POST', 'PUT']:
            if request.is_json:
                try:
                    data = request.get_json(silent=True)
                    if data:
                        # Mask sensitive data
                        if 'password' in data:
                            data['password'] = '***'
                        if 'consumer_secret' in data:
                            data['consumer_secret'] = '***'
                        logger.debug(f"📋 Request data: {data}")
                except:
                    pass

    @app.after_request
    def log_response(response):
        """Log all responses (development only)."""
        logger.debug(f"← {request.method} {request.path} - {response.status_code}")
        return response
else:
    logger.info("ℹ️ Request logging disabled in production mode")


# ─── Health Check ─────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint with system status."""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'environment': os.getenv('FLASK_ENV', 'production'),
        'redis_connected': bool(REDIS_URL and REDIS_URL.startswith("redis")),
        'mpesa_configured': all([
            os.getenv('MPESA_CONSUMER_KEY'),
            os.getenv('MPESA_CONSUMER_SECRET'),
            os.getenv('MPESA_PASSKEY'),
            os.getenv('MPESA_SHORTCODE'),
            os.getenv('MPESA_CALLBACK_URL')
        ]),
        'missing_env_vars': MISSING_ENV_VARS
    }), 200


# ─── Register Blueprints (SAFE WITH CORRECT GUARD) ──────────
mpesa_loaded = False

def register_blueprints():
    """Safely register blueprints with error handling and correct guard."""
    global mpesa_loaded
    
    try:
        # ✅ CORRECT guard: blueprint name is 'mpesa' (from Blueprint('mpesa', __name__))
        if 'mpesa' not in app.blueprints:
            from api.routes.mpesa import mpesa_bp
            app.register_blueprint(mpesa_bp, url_prefix='/api/mpesa')
            mpesa_loaded = True
            logger.info("✅ M-Pesa routes registered successfully")
        else:
            mpesa_loaded = True
            logger.info("ℹ️ M-Pesa blueprint already registered")
    except ImportError as e:
        logger.critical(f"❌ CRITICAL: Failed to import mpesa blueprint: {e}")
        logger.critical("❌ Payment system NOT loaded!")
    except Exception as e:
        logger.critical(f"❌ CRITICAL: Failed to register mpesa blueprint: {e}")
        logger.critical("❌ Payment system NOT loaded!")

# ─── Register Error Handlers ──────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404: {request.path}")
    return jsonify({'error': 'Resource not found', 'path': request.path}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500: {request.path} - {error}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def rate_limit_error(error):
    logger.warning(f"429 Rate limit exceeded: {request.path} from {request.remote_addr}")
    return jsonify({
        'error': 'Too many requests. Please try again later.',
        'retry_after': 60
    }), 429


# ─── Application Factory ──────────────────────────────────────
def create_app():
    """Application factory for better testing and scaling."""
    # Register blueprints
    register_blueprints()
    
    # Log startup with payment system status
    logger.info("🚀 AUTO-V Backend Started")
    logger.info(f"📡 Environment: {os.getenv('FLASK_ENV', 'production')}")
    logger.info(f"📡 Port: {os.getenv('PORT', 10000)}")
    
    if mpesa_loaded:
        logger.info("✅ Payment system loaded successfully")
    else:
        logger.critical("❌ CRITICAL: Payment system NOT loaded!")
    
    return app


# ─── Main Entry Point ─────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    
    # Create app with factory
    app = create_app()
    
    # Run app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_ENV') == 'development'
    )
