# api/__init__.py – AUTO-V Flask Application (PRODUCTION READY with Redis)

import os
import logging
import sys
import signal
from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ─── Logging with Rotation ──────────────────────────────────
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
REDIS_URL = os.getenv('REDIS_URL')
USE_REDIS = REDIS_URL is not None

if USE_REDIS:
    try:
        # Test Redis connection
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

# ─── App ────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['JSON_SORT_KEYS'] = False

# ─── CORS ────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)
logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

# Initialize rate limiter
limiter.init_app(app)

# ─── Error Handlers ─────────────────────────────────────────
@app.errorhandler(RateLimitExceeded)
def handle_rate_limit_exceeded(e):
    """Handle rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded for {request.remote_addr}")
    return jsonify({
        'error': 'Too many requests. Please slow down.',
        'code': 'RATE_LIMIT_EXCEEDED',
        'retry_after': e.retry_after if hasattr(e, 'retry_after') else None
    }), 429

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'error': 'Resource not found',
        'code': 'NOT_FOUND',
        'path': request.path
    }), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR'
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler for unexpected errors."""
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({
        'error': 'An unexpected error occurred',
        'code': 'UNEXPECTED_ERROR'
    }), 500

# ─── Request Logging ────────────────────────────────────────
@app.before_request
def log_request():
    """Log all incoming requests."""
    logger.info(f"→ {request.method} {request.path} - {request.remote_addr}")

@app.after_request
def log_response(response):
    """Log all outgoing responses."""
    logger.info(f"← {request.method} {request.path} - {response.status_code}")
    return response

# ─── Security Headers ──────────────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Server'] = 'AUTO-V'
    return response

# ─── Import Blueprints ──────────────────────────────────────
from api.routes.auth import auth_bp
from api.routes.mpesa import mpesa_bp
from api.routes.payments import payments_bp
from api.routes.valuations import valuations_bp
from api.routes.inspections import inspections_bp
from api.routes.assessments import assessments_bp
from api.routes.mileage import mileage_bp
from api.routes.intelligence import intelligence_bp
from api.routes.admin import admin_bp

# ─── Register Blueprints ──────────────────────────────────
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(mpesa_bp, url_prefix='/api/mpesa')
app.register_blueprint(payments_bp, url_prefix='/api/payments')
app.register_blueprint(valuations_bp, url_prefix='/api/valuations')
app.register_blueprint(inspections_bp, url_prefix='/api/inspections')
app.register_blueprint(assessments_bp, url_prefix='/api/assessments')
app.register_blueprint(mileage_bp, url_prefix='/api/mileage')
app.register_blueprint(intelligence_bp, url_prefix='/api/intelligence')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# ─── Health Checks ──────────────────────────────────────────
from services.mpesa import is_mpesa_configured
from services.supabase_client import get_supabase

@app.route('/api/health', methods=['GET'])
@limiter.limit("60 per minute")
def health_check():
    """Basic health check."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'environment': os.getenv('FLASK_ENV', 'development')
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
        supabase = get_supabase()
        supabase.table('system_settings').select('count').limit(1).execute()
        checks['services']['supabase'] = {'status': 'healthy'}
    except Exception as e:
        checks['services']['supabase'] = {'status': 'unhealthy', 'error': str(e)}
        checks['status'] = 'degraded'
    
    # Check M-Pesa
    checks['services']['mpesa'] = {
        'status': 'configured' if is_mpesa_configured() else 'missing_credentials',
        'environment': os.getenv('MPESA_ENV', 'not_set')
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

@app.route('/')
def root():
    return jsonify({
        'service': 'AUTO-V Backend',
        'version': '2.0.0',
        'status': 'running',
        'endpoints': {
            'auth': '/api/auth',
            'payments': '/api/payments',
            'mpesa': '/api/mpesa',
            'valuations': '/api/valuations',
            'inspections': '/api/inspections',
            'assessments': '/api/assessments',
            'mileage': '/api/mileage',
            'intelligence': '/api/intelligence',
            'admin': '/api/admin',
            'health': '/api/health'
        }
    })

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

# ─── Run ────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
