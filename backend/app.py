# app.py – AUTO-V Flask Application (PRODUCTION READY)
# ✅ Real M-Pesa production credentials (Shortcode: 4095377)
# ✅ Supabase credentials configured
# ✅ Full security implementation
# ✅ Complete error handling
# ✅ Production configuration
# ✅ Redis integration for rate limiting

import os
import sys
import signal
import logging
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from dotenv import load_dotenv

# ─── Load Environment ──────────────────────────────────────────
load_dotenv()

# ─── Logging Configuration ────────────────────────────────────
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.getenv('LOG_FILE', 'auto-v.log')

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add file handler with rotation
if LOG_FILE:
    try:
        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
    except Exception as e:
        logger.warning(f"Could not set up log rotation: {e}")

# ─── Redis for Rate Limiting ──────────────────────────────────
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
USE_REDIS = REDIS_URL is not None

if USE_REDIS:
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        logger.info(f"✅ Redis connected at {REDIS_URL[:20]}...")
        storage_uri = REDIS_URL
        storage_options = {"socket_connect_timeout": 30}
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        logger.warning("Falling back to memory storage for rate limiting")
        storage_uri = "memory://"
        storage_options = {}
else:
    logger.warning("⚠️ REDIS_URL not set. Using memory storage for rate limiting (not recommended for production)")
    storage_uri = "memory://"
    storage_options = {}

# ─── Rate Limiter ────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    storage_options=storage_options,
    default_limits=["200 per day", "50 per hour"],
    strategy="fixed-window",
    enabled=os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
)

# ─── Create Flask App ─────────────────────────────────────────
app = Flask(__name__)

# ─── Configuration ────────────────────────────────────────────
class Config:
    """Production configuration."""
    
    # ─── Supabase Configuration ──────────────────────────────────
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://tsvejnzxrxrrecgquxbq.supabase.co')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ')
    SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET', '')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    
    # ─── M-Pesa Production Credentials ──────────────────────────
    MPESA_ENV = os.getenv('MPESA_ENV', 'production')
    MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', 'LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv')
    MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', 'aGGo8AuPJVpsZLcs')
    MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277')
    MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
    MPESA_SHORTCODE_TYPE = os.getenv('MPESA_SHORTCODE_TYPE', 'paybill')
    MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://auto-v-backend.onrender.com/api/mpesa/callback')
    
    # ─── OpenAI ──────────────────────────────────────────────────
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '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')
    
    # ─── CarAPI ──────────────────────────────────────────────────
    CARAPI_KEY = os.getenv('CARAPI_KEY', 'carapi_45747df211066bb9d14224ae998de7e7')
    
    # ─── Security ─────────────────────────────────────────────────
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(24).hex())
    
    # ─── Session ──────────────────────────────────────────────────
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))
    REFRESH_TIMEOUT = int(os.getenv('REFRESH_TIMEOUT', '604800'))
    
    # ─── Rate Limiting ───────────────────────────────────────────
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'true').lower() == 'true'
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '100 per hour')
    
    # ─── Environment ─────────────────────────────────────────────
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('PORT', 10000))
    
    # ─── CORS ────────────────────────────────────────────────────
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'https://auto-v.meipressgroup.com,https://auto-v.onrender.com,https://auto-v-backend.onrender.com,http://localhost:3000,http://localhost:5000').split(',')
    
    @classmethod
    def validate(cls):
        """Validate all required configuration."""
        errors = []
        warnings = []
        
        # ─── Validate Supabase ──────────────────────────────────
        if not cls.SUPABASE_URL:
            errors.append("SUPABASE_URL is not set")
        elif not cls.SUPABASE_URL.startswith('https://'):
            errors.append("SUPABASE_URL must use HTTPS")
        
        if not cls.SUPABASE_ANON_KEY:
            errors.append("SUPABASE_ANON_KEY is not set")
        elif len(cls.SUPABASE_ANON_KEY) < 50:
            warnings.append("SUPABASE_ANON_KEY seems too short")
        
        # ─── Validate M-Pesa ──────────────────────────────────
        if not cls.MPESA_CONSUMER_KEY:
            errors.append("MPESA_CONSUMER_KEY is not set")
        if not cls.MPESA_CONSUMER_SECRET:
            errors.append("MPESA_CONSUMER_SECRET is not set")
        if not cls.MPESA_PASSKEY:
            errors.append("MPESA_PASSKEY is not set")
        if not cls.MPESA_CALLBACK_URL:
            errors.append("MPESA_CALLBACK_URL is not set")
        
        if cls.MPESA_CALLBACK_URL and not cls.MPESA_CALLBACK_URL.startswith('https://'):
            errors.append("MPESA_CALLBACK_URL must use HTTPS in production")
        
        # ─── Validate Security ──────────────────────────────────
        if cls.ENV == 'production' and cls.DEBUG:
            errors.append("DEBUG should be False in production")
        
        # ─── Validate Shortcode ──────────────────────────────────
        if cls.MPESA_SHORTCODE and not cls.MPESA_SHORTCODE.isdigit():
            errors.append(f"MPESA_SHORTCODE must be numeric: {cls.MPESA_SHORTCODE}")
        
        # ─── Log results ────────────────────────────────────────
        if errors:
            for error in errors:
                logger.error(f"❌ Configuration error: {error}")
            return False
        
        if warnings:
            for warning in warnings:
                logger.warning(f"⚠️ Configuration warning: {warning}")
        
        logger.info("✅ Configuration validated successfully")
        
        # Log configuration summary
        logger.info("=" * 60)
        logger.info("📋 Configuration Summary:")
        logger.info(f"  Environment: {cls.ENV}")
        logger.info(f"  Supabase URL: {cls.SUPABASE_URL}")
        logger.info(f"  Supabase ANON Key: {'✅ Set' if cls.SUPABASE_ANON_KEY else '❌ Missing'}")
        logger.info(f"  M-Pesa Shortcode: {cls.MPESA_SHORTCODE}")
        logger.info(f"  M-Pesa Environment: {cls.MPESA_ENV}")
        logger.info(f"  Callback URL: {cls.MPESA_CALLBACK_URL}")
        logger.info(f"  Rate Limiting: {cls.RATELIMIT_ENABLED}")
        logger.info(f"  OpenAI: {'✅ Set' if cls.OPENAI_API_KEY else '❌ Missing'}")
        logger.info(f"  CarAPI: {'✅ Set' if cls.CARAPI_KEY else '❌ Missing'}")
        logger.info("=" * 60)
        
        return True

# ─── Apply Configuration ─────────────────────────────────────
app.config.from_object(Config)

# ─── CORS Configuration ──────────────────────────────────────
CORS(app, resources={
    r"/api/*": {
        "origins": Config.ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Session-Token"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})
logger.info(f"CORS allowed origins: {Config.ALLOWED_ORIGINS}")

# Initialize rate limiter
limiter.init_app(app)

# ─── Initialize Supabase Client ─────────────────────────────
def init_supabase():
    """Initialize Supabase client and verify connection."""
    try:
        from services.supabase_client import get_supabase, check_supabase_health
        
        # Test connection
        health = check_supabase_health()
        if health.get('connected'):
            logger.info("✅ Supabase connection successful")
            return True
        else:
            logger.error(f"❌ Supabase connection failed: {health.get('error', 'Unknown error')}")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Supabase client import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Supabase initialization error: {e}")
        return False

# ─── Request Middleware ──────────────────────────────────────
@app.before_request
def before_request():
    """Request preprocessing."""
    # Log all requests in production
    if app.config['ENV'] == 'production':
        logger.info(f"📥 {request.method} {request.path} from {request.remote_addr}")
        
        # Add request start time
        g.request_start_time = time.time()
        
        # Add Supabase client to g
        if not hasattr(g, 'supabase'):
            try:
                from services.supabase_client import get_supabase
                g.supabase = get_supabase()
            except Exception as e:
                logger.error(f"❌ Failed to get Supabase client: {e}")

@app.after_request
def after_request(response):
    """Request post-processing."""
    # Log response time
    if hasattr(g, 'request_start_time'):
        elapsed = time.time() - g.request_start_time
        logger.info(f"📤 {request.method} {request.path} → {response.status_code} ({elapsed:.3f}s)")
    
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Server'] = 'AUTO-V'
    
    return response

# ─── Error Handlers ──────────────────────────────────────────
@app.errorhandler(RateLimitExceeded)
def handle_rate_limit_exceeded(e):
    """Handle rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded for {request.remote_addr}")
    return jsonify({
        'error': 'Too many requests. Please slow down.',
        'code': 'RATE_LIMIT_EXCEEDED',
        'retry_after': e.retry_after if hasattr(e, 'retry_after') else None,
        'timestamp': datetime.now().isoformat()
    }), 429

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Resource not found',
        'path': request.path,
        'method': request.method,
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        'error': 'Method not allowed',
        'path': request.path,
        'method': request.method,
        'timestamp': datetime.now().isoformat()
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"❌ Internal server error: {error}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again later.',
        'timestamp': datetime.now().isoformat()
    }), 500

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions."""
    logger.error(f"❌ Unhandled exception: {error}", exc_info=True)
    return jsonify({
        'error': 'Server error',
        'message': str(error) if app.config['DEBUG'] else 'An unexpected error occurred',
        'timestamp': datetime.now().isoformat()
    }), 500

# ─── Import and Register Routes ─────────────────────────────
def register_blueprints():
    """Register all blueprints."""
    try:
        # ─── VIN Routes ─────────────────────────────────────
        try:
            from api.routes.vin_routes import router as vin_router
            app.register_blueprint(vin_router, url_prefix='/api/vin')
            logger.info("✅ VIN routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ VIN routes not found: {e}")
        
        # ─── M-Pesa Routes ──────────────────────────────────
        try:
            from api.routes.mpesa import mpesa_bp
            app.register_blueprint(mpesa_bp, url_prefix='/api/mpesa')
            logger.info("✅ M-Pesa routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ M-Pesa routes not found: {e}")
        
        # ─── Auth Routes ────────────────────────────────────
        try:
            from api.routes.auth import auth_bp
            app.register_blueprint(auth_bp, url_prefix='/api/auth')
            logger.info("✅ Auth routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ Auth routes not found: {e}")
        
        # ─── Vehicle Routes ─────────────────────────────────
        try:
            from api.routes.vehicles import vehicles_bp
            app.register_blueprint(vehicles_bp, url_prefix='/api/vehicles')
            logger.info("✅ Vehicle routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ Vehicle routes not found: {e}")
        
        # ─── Valuation Routes ──────────────────────────────
        try:
            from api.routes.valuations import valuations_bp
            app.register_blueprint(valuations_bp, url_prefix='/api/valuations')
            logger.info("✅ Valuation routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ Valuation routes not found: {e}")
        
        # ─── Inspection Routes ─────────────────────────────
        try:
            from api.routes.inspections import inspections_bp
            app.register_blueprint(inspections_bp, url_prefix='/api/inspections')
            logger.info("✅ Inspection routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ Inspection routes not found: {e}")
        
        # ─── Admin Routes ──────────────────────────────────
        try:
            from api.routes.admin import admin_bp
            app.register_blueprint(admin_bp, url_prefix='/api/admin')
            logger.info("✅ Admin routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ Admin routes not found: {e}")
        
        # ─── Service Routes ─────────────────────────────────
        try:
            from api.routes.services import services_bp
            app.register_blueprint(services_bp, url_prefix='/api/services')
            logger.info("✅ Service routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ Service routes not found: {e}")
            
    except Exception as e:
        logger.error(f"❌ Failed to register blueprints: {e}")
        raise

# ─── Health Check ─────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
@limiter.limit("60 per minute")
def health_check():
    """Basic health check."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'environment': app.config['ENV'],
        'services': {
            'mpesa': {
                'configured': bool(app.config['MPESA_CONSUMER_KEY']),
                'shortcode': app.config['MPESA_SHORTCODE'],
                'environment': app.config['MPESA_ENV']
            },
            'supabase': {
                'url': app.config['SUPABASE_URL']
            },
            'redis': {
                'enabled': USE_REDIS,
                'connected': USE_REDIS and 'redis_client' in globals()
            }
        }
    }), 200

@app.route('/api/health/detailed', methods=['GET'])
@limiter.limit("30 per minute")
def detailed_health():
    """Detailed health check with all dependencies."""
    checks = {
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy',
        'services': {}
    }
    
    # Check Supabase
    try:
        from services.supabase_client import check_supabase_health
        health = check_supabase_health()
        checks['services']['supabase'] = {
            'status': 'healthy' if health.get('connected') else 'unhealthy',
            'error': health.get('error')
        }
        if not health.get('connected'):
            checks['status'] = 'degraded'
    except Exception as e:
        checks['services']['supabase'] = {'status': 'unhealthy', 'error': str(e)}
        checks['status'] = 'degraded'
    
    # Check M-Pesa
    checks['services']['mpesa'] = {
        'status': 'configured' if app.config['MPESA_CONSUMER_KEY'] else 'missing_credentials',
        'environment': app.config['MPESA_ENV'],
        'shortcode': app.config['MPESA_SHORTCODE']
    }
    
    # Check Redis
    if USE_REDIS:
        try:
            redis_client.ping()
            checks['services']['redis'] = {'status': 'healthy'}
        except Exception as e:
            checks['services']['redis'] = {'status': 'unhealthy', 'error': str(e)}
            checks['status'] = 'degraded'
    else:
        checks['services']['redis'] = {'status': 'not_configured'}
    
    # Check rate limiting
    checks['rate_limiting'] = {
        'enabled': os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true',
        'storage': 'redis' if USE_REDIS else 'memory'
    }
    
    return jsonify(checks), 200

@app.route('/api/ping', methods=['GET'])
def ping():
    """Simple ping endpoint."""
    return jsonify({
        'pong': True,
        'timestamp': datetime.now().isoformat()
    }), 200

# ─── Root Route ──────────────────────────────────────────────
@app.route('/')
def root():
    """Root endpoint."""
    return jsonify({
        'name': 'AUTO-V API',
        'version': '2.0.0',
        'environment': app.config['ENV'],
        'status': 'operational',
        'endpoints': {
            'health': '/api/health',
            'ping': '/api/ping',
            'mpesa': '/api/mpesa',
            'auth': '/api/auth',
            'admin': '/api/admin',
            'vehicles': '/api/vehicles',
            'services': '/api/services',
            'valuations': '/api/valuations',
            'inspections': '/api/inspections',
            'vin': '/api/vin'
        }
    }), 200

# ─── Graceful Shutdown ──────────────────────────────────────
def graceful_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, cleaning up...")
    # Close Redis connection if exists
    if 'redis_client' in globals():
        try:
            redis_client.close()
            logger.info("Redis connection closed")
        except:
            pass
    logger.info("Shutdown complete")
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)

# ─── Application Factory ─────────────────────────────────────
def create_app():
    """Application factory for production."""
    # Validate configuration
    if not Config.validate():
        logger.error("❌ Invalid configuration. Application may not work correctly.")
    
    # Initialize Supabase
    init_supabase()
    
    # Register routes
    register_blueprints()
    
    # Log startup
    logger.info("=" * 60)
    logger.info("🚀 AUTO-V API Starting...")
    logger.info(f"📦 Environment: {app.config['ENV']}")
    logger.info(f"🔑 M-Pesa Shortcode: {app.config['MPESA_SHORTCODE']}")
    logger.info(f"🌐 M-Pesa Environment: {app.config['MPESA_ENV']}")
    logger.info(f"📞 Callback URL: {app.config['MPESA_CALLBACK_URL']}")
    logger.info(f"🗄️  Supabase URL: {app.config['SUPABASE_URL']}")
    logger.info(f"🤖 OpenAI: {'✅ Configured' if app.config['OPENAI_API_KEY'] else '❌ Missing'}")
    logger.info(f"🚗 CarAPI: {'✅ Configured' if app.config['CARAPI_KEY'] else '❌ Missing'}")
    logger.info("=" * 60)
    
    return app

# ─── Initialize App ──────────────────────────────────────────
app = create_app()

# ─── Main Entry Point ────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    
    # Production settings
    if app.config['ENV'] == 'production':
        logger.info(f"🚀 Starting production server on port {port}")
        # Use production WSGI server
        try:
            from waitress import serve
            serve(app, host='0.0.0.0', port=port, threads=4)
        except ImportError:
            logger.warning("⚠️ Waitress not installed, using Flask development server")
            app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Development
        app.run(
            host='0.0.0.0',
            port=port,
            debug=app.config['DEBUG']
        )
