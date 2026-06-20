# app.py - Enterprise-Grade Flask Application (FINAL)

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
REQUIRED_ENV_VARS = {
    'MPESA_CONSUMER_KEY': 'M-Pesa Consumer Key',
    'MPESA_CONSUMER_SECRET': 'M-Pesa Consumer Secret',
    'MPESA_PASSKEY': 'M-Pesa Passkey',
    'MPESA_SHORTCODE': 'M-Pesa Shortcode',
    'MPESA_CALLBACK_URL': 'M-Pesa Callback URL',
    'SUPABASE_URL': 'Supabase URL',
    'SUPABASE_ANON_KEY': 'Supabase Anon Key'
}

OPTIONAL_ENV_VARS = {
    'REDIS_URL': 'Redis URL',
    'MPESA_ENV': 'M-Pesa Environment (sandbox/production)',
    'MPESA_API_SECRET': 'M-Pesa API Secret (for signature verification)',
    'FLASK_ENV': 'Flask Environment',
    'LOG_LEVEL': 'Log Level'
}

MISSING_ENV_VARS = []

def validate_environment():
    """Validate required environment variables (called once at startup)."""
    global MISSING_ENV_VARS
    missing = []
    
    for var, description in REQUIRED_ENV_VARS.items():
        if not os.getenv(var):
            missing.append(f"{var} ({description})")
    
    MISSING_ENV_VARS = missing
    
    if missing:
        logger.warning(f"⚠️ Missing required environment variables:")
        for item in missing:
            logger.warning(f"   - {item}")
        logger.warning("⚠️ Some features may not work correctly")
    else:
        logger.info("✅ All required environment variables are set")
    
    # Log optional variables status
    for var, description in OPTIONAL_ENV_VARS.items():
        if os.getenv(var):
            logger.info(f"✅ {description}: {var[:10]}...")
        else:
            logger.info(f"ℹ️ {description}: not set (using default)")
    
    return missing

# ─── Run validation ONCE at startup ──────────────────────────
validate_environment()


# ─── CORS Configuration ──────────────────────────────────────
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


# ─── Rate Limiter Configuration (FIXED) ──────────────────────
REDIS_URL = os.getenv('REDIS_URL', None)

# ✅ Better Redis validation
if REDIS_URL and (REDIS_URL.startswith("redis://") or REDIS_URL.startswith("rediss://")):
    storage_uri = REDIS_URL
    logger.info(f"✅ Using Redis for rate limiting: {REDIS_URL[:30]}...")
else:
    storage_uri = "memory://"
    if REDIS_URL:
        logger.warning(f"⚠️ Invalid Redis URL format: {REDIS_URL}. Using memory storage.")
    else:
        logger.warning("⚠️ Using memory for rate limiting (not production-safe)")

# ✅ Correct Limiter initialization for v3+
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per hour", "100 per minute"],
    storage_uri=storage_uri
)

# Initialize with app
limiter.init_app(app)
logger.info("✅ Rate limiter initialized successfully")


# ─── Security Middleware ──────────────────────────────────────

# ─── Request Size Limit ──────────────────────────────────────
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

# ─── Request Logging Middleware (DEV ONLY) ────────────────────
if os.getenv("FLASK_ENV") == "development":
    @app.before_request
    def log_request():
        """Log all incoming requests (development only)."""
        logger.debug(f"→ {request.method} {request.path} - {request.remote_addr}")
        
        # Log request body for payment endpoints
        if request.path.startswith('/api/mpesa') and request.method in ['POST', 'PUT']:
            if request.is_json:
                try:
                    data = request.get_json(silent=True)
                    if data:
                        # Mask sensitive data
                        sensitive_keys = ['password', 'consumer_secret', 'api_key', 'pin']
                        for key in sensitive_keys:
                            if key in data:
                                data[key] = '***'
                        logger.debug(f"📋 Request data: {data}")
                except:
                    pass

    @app.after_request
    def log_response(response):
        logger.debug(f"← {request.method} {request.path} - {response.status_code}")
        return response
else:
    logger.info("ℹ️ Request logging disabled in production mode")


# ─── Health Check ─────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check with detailed system status."""
    # Check Redis connectivity
    redis_healthy = False
    if REDIS_URL and (REDIS_URL.startswith("redis://") or REDIS_URL.startswith("rediss://")):
        try:
            import redis
            r = redis.from_url(REDIS_URL)
            redis_healthy = r.ping()
        except:
            redis_healthy = False
    
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'environment': os.getenv('FLASK_ENV', 'production'),
        'redis_connected': redis_healthy,
        'mpesa_configured': all([
            os.getenv('MPESA_CONSUMER_KEY'),
            os.getenv('MPESA_CONSUMER_SECRET'),
            os.getenv('MPESA_PASSKEY'),
            os.getenv('MPESA_SHORTCODE'),
            os.getenv('MPESA_CALLBACK_URL')
        ]),
        'missing_env_vars': MISSING_ENV_VARS
    }), 200


# ─── Register Blueprints ──────────────────────────────────────
mpesa_loaded = False

def register_blueprints():
    global mpesa_loaded
    try:
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
        mpesa_loaded = False
    except Exception as e:
        logger.critical(f"❌ CRITICAL: Failed to register mpesa blueprint: {e}")
        mpesa_loaded = False
    
    # ✅ Fail fast in production
    if os.getenv("FLASK_ENV") == "production" and not mpesa_loaded:
        raise RuntimeError("🚨 M-Pesa payment system failed to load - application cannot start in production mode!")


# ─── Register Error Handlers ──────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404: {request.path}")
    return jsonify({'error': 'Resource not found', 'path': request.path}), 404

@app.errorhandler(413)
def request_too_large(error):
    logger.warning(f"413: Request too large - {request.path}")
    return jsonify({'error': 'Request too large. Maximum size is 10MB'}), 413

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
    register_blueprints()
    
    logger.info("=" * 60)
    logger.info("🚀 AUTO-V Backend Started")
    logger.info(f"📡 Environment: {os.getenv('FLASK_ENV', 'production')}")
    logger.info(f"📡 Port: {os.getenv('PORT', 10000)}")
    
    if mpesa_loaded:
        logger.info("✅ Payment system loaded successfully")
    else:
        logger.critical("❌ CRITICAL: Payment system NOT loaded!")
    
    logger.info("=" * 60)
    
    return app


# ─── Main Entry Point ─────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_ENV') == 'development'
    )
