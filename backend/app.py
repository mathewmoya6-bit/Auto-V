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

# ─── Load Environment ──────────────────────────────────────────
load_dotenv()

# ─── Logging Configuration ────────────────────────────────────
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

# ─── Redis for Rate Limiting ──────────────────────────────────
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
    strategy="fixed-window",
    enabled=os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
)

# ─── Create Flask App ─────────────────────────────────────────
app = Flask(__name__)

# ─── Configuration ────────────────────────────────────────────
class Config:
    """Production configuration."""
    
    # ─── Supabase ──────────────────────────────────────────────────
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # ─── M-Pesa ──────────────────────────────────────────────────
    MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
    MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
    MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
    MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
    MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://auto-v.meipressgroup.com/mpesa/callback')
    MPESA_ENV = os.getenv('MPESA_ENV', 'production')
    
    # ─── Security ─────────────────────────────────────────────────
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(24).hex())
    
    # ─── Environment ─────────────────────────────────────────────
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('PORT', 10000))
    
    # ─── CORS ────────────────────────────────────────────────────
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'https://auto-v.meipressgroup.com,https://auto-v.onrender.com,https://auto-v-backend.onrender.com,http://localhost:3000,http://localhost:5000').split(',')
    
    @classmethod
    def validate(cls):
        """Validate configuration."""
        errors = []
        warnings = []
        
        if not cls.SUPABASE_URL:
            errors.append("SUPABASE_URL is not set")
        if not cls.SUPABASE_ANON_KEY:
            errors.append("SUPABASE_ANON_KEY is not set")
        if cls.ENV == 'production' and cls.DEBUG:
            errors.append("DEBUG should be False in production")
        
        if errors:
            for error in errors:
                logger.error(f"❌ {error}")
            return False
        
        if warnings:
            for warning in warnings:
                logger.warning(f"⚠️ {warning}")
        
        return True

# ─── Apply Configuration ─────────────────────────────────────
app.config.from_object(Config)

# ─── CORS Configuration ──────────────────────────────────────
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
    """Handle OPTIONS preflight requests."""
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response

# Initialize rate limiter
limiter.init_app(app)

# ─── Initialize Supabase ──────────────────────────────────────
def init_supabase():
    """Initialize Supabase client and verify connection."""
    try:
        from services.supabase import get_supabase
        client = get_supabase()
        logger.info("✅ Supabase client initialized")
        return True
    except ImportError as e:
        logger.warning(f"⚠️ Supabase client not available: {e}")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Supabase init warning: {e}")
        return False

# ─── Request Middleware ──────────────────────────────────────
@app.before_request
def before_request():
    """Request preprocessing."""
    if app.config['ENV'] == 'production':
        logger.info(f"📥 {request.method} {request.path}")
    g.request_start_time = time.time()

@app.after_request
def after_request(response):
    """Request post-processing."""
    if hasattr(g, 'request_start_time'):
        elapsed = time.time() - g.request_start_time
        logger.info(f"📤 {request.method} {request.path} → {response.status_code} ({elapsed:.3f}s)")
    
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Server'] = 'AUTO-V'
    return response

# ─── Error Handlers ──────────────────────────────────────────
@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    """Handle rate limit exceeded."""
    return jsonify({
        'error': 'Too many requests. Please slow down.',
        'code': 'RATE_LIMIT_EXCEEDED',
        'retry_after': 60
    }), 429

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Resource not found',
        'path': request.path,
        'method': request.method
    }), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    logger.error(f"❌ Internal error: {e}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again later.'
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions."""
    logger.error(f"❌ Unhandled exception: {e}", exc_info=True)
    return jsonify({
        'error': 'Server error',
        'message': 'An unexpected error occurred'
    }), 500

# ─── HEALTH ROUTES ────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health_check():
    """Basic health check."""
    try:
        from services.mpesa import is_mpesa_configured
        mpesa_status = is_mpesa_configured()
    except:
        mpesa_status = False
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'environment': app.config['ENV'],
        'services': {
            'mpesa': {
                'configured': mpesa_status,
                'environment': app.config['MPESA_ENV'],
                'shortcode': app.config['MPESA_SHORTCODE']
            },
            'supabase': 'connected' if init_supabase() else 'disconnected'
        }
    }), 200

@app.route('/api/ping', methods=['GET'])
def ping():
    """Simple ping endpoint."""
    return jsonify({
        'pong': True,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/')
def root():
    """Root endpoint."""
    return jsonify({
        'name': 'AUTO-V API',
        'version': '2.0.0',
        'status': 'operational',
        'environment': app.config['ENV'],
        'endpoints': {
            'health': '/api/health',
            'ping': '/api/ping',
            'mpesa_initiate': '/api/mpesa/initiate',
            'mpesa_status': '/api/mpesa/status/<payment_id>',
            'mpesa_auto_confirm': '/api/mpesa/auto-confirm/<payment_id>',
            'mpesa_callback': '/mpesa/callback'
        }
    }), 200

# ─── M-PESA ROUTES ────────────────────────────────────────────

@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa STK Push callback."""
    from services.mpesa import handle_mpesa_callback, verify_safaricom_ip
    
    try:
        client_ip = request.remote_addr or request.headers.get('X-Forwarded-For', '')
        logger.info(f"📥 M-Pesa callback received from IP: {client_ip}")
        
        # Verify IP (optional - can be disabled for testing)
        # if not verify_safaricom_ip(client_ip):
        #     logger.warning(f"⚠️ Invalid IP: {client_ip}")
        #     return jsonify({"ResultCode": 1, "ResultDesc": "Invalid IP"}), 403
        
        callback_data = request.get_json()
        if not callback_data:
            logger.error("❌ No JSON data in callback")
            return jsonify({"ResultCode": 1, "ResultDesc": "No data"}), 400
        
        result = handle_mpesa_callback(callback_data, client_ip)
        logger.info(f"✅ Callback processed: {result}")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"❌ Callback endpoint error: {e}", exc_info=True)
        return jsonify({"ResultCode": 1, "ResultDesc": str(e)}), 500


@app.route('/api/mpesa/initiate', methods=['POST'])
@limiter.limit("10 per minute", key_func=lambda: request.headers.get('Authorization', ''))
def initiate_payment():
    """Initiate M-Pesa STK Push payment."""
    from services.mpesa import initiate_stk_push, get_supabase
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['phone', 'amount', 'payment_id']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Initiate STK Push
        result = initiate_stk_push(
            phone=data['phone'],
            amount=data['amount'],
            payment_id=data['payment_id'],
            service=data.get('service', 'AUTO-V'),
            reference=data.get('reference')
        )
        
        # Save transaction to database
        supabase = get_supabase()
        try:
            payment_data = {
                'id': data['payment_id'],
                'amount': data['amount'],
                'phone': data['phone'],
                'service': data.get('service', 'AUTO-V'),
                'purpose': data.get('purpose'),
                'client_type': data.get('client_type', 'individual'),
                'reference': data.get('reference'),
                'checkout_request_id': result.get('CheckoutRequestID'),
                'merchant_request_id': result.get('MerchantRequestID'),
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            supabase.table('payments').insert(payment_data).execute()
            logger.info(f"✅ Payment record saved: {data['payment_id']}")
        except Exception as e:
            logger.warning(f"⚠️ Could not save payment record: {e}")
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Payment initiation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/mpesa/status/<payment_id>', methods=['GET'])
@limiter.limit("15 per minute", key_func=lambda: request.headers.get('Authorization', ''))
def payment_status(payment_id):
    """Get payment status with auto-verification."""
    from services.mpesa import get_payment_status
    
    try:
        # Get auth token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        result = get_payment_status(payment_id)
        
        if result.get('status') == 'not_found':
            return jsonify({'error': 'Payment not found'}), 404
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Status query error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/mpesa/auto-confirm/<payment_id>', methods=['POST'])
@limiter.limit("5 per minute", key_func=lambda: request.headers.get('Authorization', ''))
def auto_confirm_payment(payment_id):
    """Auto-confirm payment by verifying with M-Pesa API."""
    from services.mpesa import auto_confirm_payment
    
    try:
        # Get auth token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        result = auto_confirm_payment(payment_id)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Auto-confirm error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mpesa/query/<checkout_id>', methods=['GET'])
@limiter.limit("10 per minute")
def query_mpesa_status(checkout_id):
    """Direct query to M-Pesa API for status."""
    from services.mpesa import query_payment_status
    
    try:
        result = query_payment_status(checkout_id)
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/mpesa/configured', methods=['GET'])
def mpesa_configured():
    """Check if M-Pesa is configured."""
    from services.mpesa import is_mpesa_configured
    
    try:
        configured = is_mpesa_configured()
        return jsonify({
            'configured': configured,
            'environment': app.config['MPESA_ENV'],
            'shortcode': app.config['MPESA_SHORTCODE']
        }), 200
        
    except Exception as e:
        return jsonify({
            'configured': False,
            'error': str(e)
        }), 200

# ─── REGISTER BLUEPRINTS ──────────────────────────────────────
def register_blueprints():
    """Register all blueprints."""
    registered = 0
    
    # ─── Mileage Routes ─────────────────────────────────────────
    try:
        from api.routes.mileage import mileage_bp
        app.register_blueprint(mileage_bp, url_prefix='/api/mileage')
        registered += 1
        logger.info("✅ Registered: /api/mileage")
    except Exception as e:
        logger.warning(f"⚠️ Mileage routes not available: {e}")
    
    return registered

# ─── GRACEFUL SHUTDOWN ──────────────────────────────────────
def graceful_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, cleaning up...")
    if USE_REDIS and 'redis_client' in globals():
        try:
            redis_client.close()
            logger.info("Redis connection closed")
        except:
            pass
    logger.info("Shutdown complete")
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)

# ─── APPLICATION FACTORY ─────────────────────────────────────
def create_app():
    """Application factory for production."""
    # Validate configuration
    if not Config.validate():
        logger.error("❌ Invalid configuration. Application may not work correctly.")
    
    # Initialize Supabase
    init_supabase()
    
    # Register routes
    registered = register_blueprints()
    
    # Log startup
    logger.info("=" * 60)
    logger.info("🚀 AUTO-V API Starting...")
    logger.info(f"📦 Environment: {app.config['ENV']}")
    logger.info(f"🔑 M-Pesa Shortcode: {app.config['MPESA_SHORTCODE']}")
    logger.info(f"🌐 M-Pesa Environment: {app.config['MPESA_ENV']}")
    logger.info(f"📞 Callback URL: {app.config['MPESA_CALLBACK_URL']}")
    logger.info(f"📋 Registered {registered} blueprints")
    logger.info("=" * 60)
    
    return app

# ─── INITIALIZE APP ──────────────────────────────────────────
app = create_app()

# ─── MAIN ENTRY POINT ────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    
    if app.config['ENV'] == 'production':
        logger.info(f"🚀 Starting production server on port {port}")
        try:
            from waitress import serve
            serve(app, host='0.0.0.0', port=port, threads=4)
        except ImportError:
            logger.warning("⚠️ Waitress not installed, using Flask development server")
            app.run(host='0.0.0.0', port=port, debug=False)
    else:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=app.config['DEBUG']
        )
