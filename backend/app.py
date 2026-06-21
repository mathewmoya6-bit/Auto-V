# app.py – AUTO-V Flask Application (PRODUCTION READY)
import os
import sys
import signal
import logging
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, g, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

# ─── Logging ──────────────────────────────────────────────────
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create logs directory
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# File handler with rotation
try:
    handler = RotatingFileHandler(LOG_FILE, maxBytes=10485760, backupCount=10)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
except Exception as e:
    logger.warning(f"Could not set up log rotation: {e}")

# ─── Redis ──────────────────────────────────────────────────
REDIS_URL = os.getenv('REDIS_URL', '')
USE_REDIS = bool(REDIS_URL)
storage_uri = REDIS_URL if USE_REDIS else "memory://"
storage_options = {}

if USE_REDIS:
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        logger.info(f"✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        storage_uri = "memory://"

# ─── Rate Limiter ────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    storage_options=storage_options,
    default_limits=["200 per day", "50 per hour"],
    enabled=os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
)

# ─── Flask App ──────────────────────────────────────────────
app = Flask(__name__)

# ─── Configuration ────────────────────────────────────────────
class Config:
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
    SUPABASE_SERVICE_ROLE = os.getenv('SUPABASE_SERVICE_ROLE', '')
    
    MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
    MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
    MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
    MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
    MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', '')
    MPESA_ENV = os.getenv('MPESA_ENV', 'production')
    
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('PORT', 10000))
    
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'https://auto-v.meipressgroup.com,https://auto-v.onrender.com,http://localhost:3000,http://localhost:5000').split(',')

app.config.from_object(Config)

# ─── CORS ──────────────────────────────────────────────────────
CORS(app, resources={
    r"/api/*": {
        "origins": Config.ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})
logger.info(f"CORS allowed origins: {Config.ALLOWED_ORIGINS}")

# ─── Manual OPTIONS Handler ──────────────────────────────────
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response

limiter.init_app(app)

# ─── Supabase Client ──────────────────────────────────────────
def init_supabase():
    try:
        from services.supabase_client import get_supabase_client
        get_supabase_client()
        logger.info("✅ Supabase client initialized")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Supabase init warning: {e}")
        return False

# ─── Request Middleware ──────────────────────────────────────
@app.before_request
def before_request():
    if app.config['ENV'] == 'production':
        logger.info(f"📥 {request.method} {request.path}")
    g.request_start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(g, 'request_start_time'):
        elapsed = time.time() - g.request_start_time
        logger.info(f"📤 {request.method} {request.path} → {response.status_code} ({elapsed:.3f}s)")
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# ─── Error Handlers ──────────────────────────────────────────
@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    return jsonify({'error': 'Too many requests', 'code': 'RATE_LIMIT_EXCEEDED'}), 429

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found', 'path': request.path}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"❌ Internal error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

# ─── Register Routes ──────────────────────────────────────────
def register_blueprints():
    try:
        from api import register_blueprints as register
        return register(app)
    except ImportError as e:
        logger.warning(f"⚠️ Route registration warning: {e}")
        return 0

# ─── Health Routes ────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'environment': app.config['ENV']
    }), 200

@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'pong': True, 'timestamp': datetime.now().isoformat()}), 200

@app.route('/')
def root():
    return jsonify({
        'name': 'AUTO-V API',
        'version': '2.0.0',
        'status': 'operational',
        'endpoints': {
            'health': '/api/health',
            'ping': '/api/ping',
            'mpesa': '/api/mpesa',
            'mileage': '/api/mileage'
        }
    }), 200

# ─── Graceful Shutdown ──────────────────────────────────────
def graceful_shutdown(signum, frame):
    logger.info("Shutting down...")
    if USE_REDIS and 'redis_client' in globals():
        try:
            redis_client.close()
        except:
            pass
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)

# ─── Application Factory ─────────────────────────────────────
def create_app():
    init_supabase()
    registered = register_blueprints()
    
    logger.info("=" * 60)
    logger.info("🚀 AUTO-V API Starting...")
    logger.info(f"📦 Environment: {app.config['ENV']}")
    logger.info(f"🔑 M-Pesa Shortcode: {app.config['MPESA_SHORTCODE']}")
    logger.info(f"📋 Registered {registered} blueprints")
    logger.info("=" * 60)
    return app

# ─── Initialize ──────────────────────────────────────────────
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    if app.config['ENV'] == 'production':
        try:
            from waitress import serve
            serve(app, host='0.0.0.0', port=port, threads=4)
        except ImportError:
            app.run(host='0.0.0.0', port=port, debug=False)
    else:
        app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
