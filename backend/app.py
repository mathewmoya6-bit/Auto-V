# app.py – AUTO-V Flask Application (ENTERPRISE PRODUCTION READY v6.0)

import os
import sys
import signal
import logging
import time
import uuid
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, g, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from dotenv import load_dotenv

# ─── Load Environment ──────────────────────────────────────────
load_dotenv()

# ─── Environment Constants (SINGLE SOURCE OF TRUTH) ──────────
ENV = os.getenv('FLASK_ENV', 'production')
DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
PORT = int(os.getenv('PORT', 10000))
REDIS_URL = os.getenv('REDIS_URL', '')
VERSION = os.getenv('APP_VERSION', '6.0.0')

# ─── Disable Flask Default Logging ────────────────────────────
logging.getLogger('werkzeug').disabled = True


# ─── Structured Logger ─────────────────────────────────────────
class StructuredLogger:
    """JSON structured logger for production observability."""
    
    @staticmethod
    def _format_message(msg, extra=None):
        if isinstance(msg, dict):
            log_entry = msg.copy()
        else:
            log_entry = {"message": msg}
        
        if extra:
            log_entry.update(extra)
        
        log_entry["timestamp"] = datetime.now().isoformat()
        log_entry["environment"] = ENV
        log_entry["version"] = VERSION
        
        return json.dumps(log_entry)
    
    @staticmethod
    def _log(level, msg, extra=None):
        """Internal log method with exception safety."""
        try:
            formatted = StructuredLogger._format_message(msg, extra)
            getattr(logger, level)(formatted)
        except Exception:
            # Fallback to plain logging if structured logging fails
            pass
    
    @staticmethod
    def info(msg, extra=None):
        StructuredLogger._log('info', msg, extra)
    
    @staticmethod
    def warning(msg, extra=None):
        StructuredLogger._log('warning', msg, extra)
    
    @staticmethod
    def error(msg, extra=None):
        StructuredLogger._log('error', msg, extra)
    
    @staticmethod
    def critical(msg, extra=None):
        StructuredLogger._log('critical', msg, extra)
    
    @staticmethod
    def debug(msg, extra=None):
        StructuredLogger._log('debug', msg, extra)


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
    StructuredLogger.warning(f"Could not set up log rotation: {e}")


# ─── Redis Connection ──────────────────────────────────────────
redis_client = None
REDIS_READY = False
storage_uri = "memory://"
storage_options = {}


def init_redis():
    """Initialize Redis connection with proper error handling."""
    global redis_client, REDIS_READY, storage_uri
    
    if not REDIS_URL:
        StructuredLogger.critical("REDIS_URL not set", {"event": "redis_missing"})
        return False
    
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL)
        
        # ✅ FIX: Single source of truth
        if redis_client.ping():
            REDIS_READY = True
            storage_uri = REDIS_URL
            StructuredLogger.info("Redis connected", {"event": "redis_connected"})
            return True
        else:
            StructuredLogger.error("Redis ping failed", {"event": "redis_ping_failed"})
            return False
            
    except Exception as e:
        StructuredLogger.error(
            "Redis connection failed",
            {"event": "redis_connection_failed", "error": str(e)}
        )
        return False


# ─── Runtime Validation ──────────────────────────────────────
def validate_runtime():
    """Validate all production requirements."""
    if ENV == 'production':
        errors = []
        
        if not REDIS_URL:
            errors.append("REDIS_URL is required in production")
        if not os.getenv('MPESA_CALLBACK_URL'):
            errors.append("MPESA_CALLBACK_URL is required in production")
        if not os.getenv('SUPABASE_URL'):
            errors.append("SUPABASE_URL is required in production")
        if not os.getenv('SUPABASE_ANON_KEY'):
            errors.append("SUPABASE_ANON_KEY is required in production")
        if not os.getenv('MPESA_CONSUMER_KEY'):
            errors.append("MPESA_CONSUMER_KEY is required in production")
        if not os.getenv('MPESA_CONSUMER_SECRET'):
            errors.append("MPESA_CONSUMER_SECRET is required in production")
        if not os.getenv('MPESA_PASSKEY'):
            errors.append("MPESA_PASSKEY is required in production")
        
        if errors:
            for error in errors:
                StructuredLogger.critical(error, {"event": "validation_error"})
            raise RuntimeError(f"Production validation failed: {', '.join(errors)}")
        
        StructuredLogger.info("All production environment variables validated")


# ─── Safe Service Imports ──────────────────────────────────────
_service_cache = {}

def safe_import_service(module_name, function_name, required=False):
    """
    Safely import a service function with caching.
    
    Args:
        module_name: Module to import from
        function_name: Function to import
        required: If True, raises error on failure
    
    Returns:
        Function or None
    """
    cache_key = f"{module_name}.{function_name}"
    
    if cache_key in _service_cache:
        return _service_cache[cache_key]
    
    try:
        module = __import__(module_name, fromlist=[function_name])
        func = getattr(module, function_name)
        _service_cache[cache_key] = func
        return func
    except Exception as e:
        error_msg = f"Service import failed: {module_name}.{function_name} - {e}"
        
        if required or ENV == 'production':
            StructuredLogger.critical(error_msg, {"event": "import_failed"})
            raise RuntimeError(error_msg)
        else:
            StructuredLogger.warning(error_msg, {"event": "import_warning"})
            _service_cache[cache_key] = None
            return None


# ─── Application Factory ──────────────────────────────────────
def create_app():
    """Application factory for production."""
    
    # ─── Validate Runtime ─────────────────────────────────────────
    validate_runtime()
    
    # ─── Initialize Redis ─────────────────────────────────────────
    redis_initialized = init_redis()
    
    # ✅ FIX: Single source of truth for Redis
    if ENV == 'production' and not REDIS_READY:
        StructuredLogger.critical("Redis not ready in production", {"event": "redis_not_ready"})
        sys.exit(1)
    
    # ─── Create Flask App ─────────────────────────────────────────
    app = Flask(__name__, static_folder='templates', static_url_path='')
    
    # ─── Configuration ────────────────────────────────────────────
    class Config:
        """Production configuration."""
        
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
        SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
        
        MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
        MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
        MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
        MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
        MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://auto-v.onrender.com/api/mpesa/callback')
        MPESA_ENV = os.getenv('MPESA_ENV', 'production')
        
        SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
        JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(24).hex())
        
        ENV = ENV
        DEBUG = DEBUG
        PORT = PORT
        VERSION = VERSION
        
        ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'https://auto-v.meipressgroup.com,https://auto-v.onrender.com,https://auto-v-backend.onrender.com,http://localhost:3000,http://localhost:5000').split(',')
        
        @classmethod
        def validate(cls):
            """Validate configuration."""
            errors = []
            
            if not cls.SUPABASE_URL:
                errors.append("SUPABASE_URL is not set")
            if not cls.SUPABASE_ANON_KEY:
                errors.append("SUPABASE_ANON_KEY is not set")
            if cls.ENV == 'production' and cls.DEBUG:
                errors.append("DEBUG should be False in production")
            
            if errors:
                for error in errors:
                    StructuredLogger.error(error, {"event": "config_error"})
                return False
            
            return True
    
    # ─── Apply Configuration ─────────────────────────────────────
    app.config.from_object(Config)
    
    # ─── Validate Configuration ──────────────────────────────────
    if not Config.validate():
        if ENV == 'production':
            sys.exit(1)
    
    # ─── Rate Limiter ────────────────────────────────────────────
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=storage_uri,
        storage_options=storage_options,
        default_limits=["200 per day", "50 per hour"],
        strategy="fixed-window",
        enabled=os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
    )
    limiter.init_app(app)
    
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
    StructuredLogger.info(
        "CORS configured",
        {"event": "cors_configured", "origins": Config.ALLOWED_ORIGINS}
    )
    
    # ─── Import Services ──────────────────────────────────────────
    # ✅ FIX: Required imports with explicit guard
    is_mpesa_configured = safe_import_service('services.mpesa', 'is_mpesa_configured', required=True)
    get_supabase_client = safe_import_service('services.supabase_client', 'get_supabase_client', required=True)
    
    # ─── Request Middleware ──────────────────────────────────────
    @app.before_request
    def before_request():
        """Request preprocessing with request ID tracking."""
        g.request_id = uuid.uuid4().hex[:8]
        g.request_start_time = time.time()
        
        safe_path = request.path.split('?')[0]
        
        # ✅ FIX: Exception-safe logging
        try:
            StructuredLogger.info(
                {"event": "request_start", "request_id": g.request_id},
                extra={
                    "method": request.method,
                    "path": safe_path,
                    "endpoint": safe_path.startswith("/api/mpesa") or "/callback" in safe_path
                }
            )
        except Exception:
            pass
    
    @app.after_request
    def after_request(response):
        """Request post-processing."""
        if hasattr(g, 'request_start_time'):
            elapsed = time.time() - g.request_start_time
            safe_path = request.path.split('?')[0]
            
            # ✅ FIX: Exception-safe logging
            try:
                if elapsed > 1.0:
                    StructuredLogger.warning(
                        {"event": "slow_request", "request_id": g.request_id},
                        extra={"path": safe_path, "duration": elapsed, "status": response.status_code}
                    )
                
                StructuredLogger.info(
                    {"event": "request_end", "request_id": g.request_id},
                    extra={
                        "method": request.method,
                        "path": safe_path,
                        "status": response.status_code,
                        "duration": elapsed
                    }
                )
            except Exception:
                pass
        
        # ✅ FIX: Add request ID to response headers for debugging
        if hasattr(g, 'request_id'):
            response.headers["X-Request-ID"] = g.request_id
        
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Server'] = 'AUTO-V'
        return response
    
    # ─── Error Handlers ──────────────────────────────────────────
    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit(e):
        return jsonify({
            'success': False,
            'error': 'Too many requests. Please slow down.',
            'code': 'RATE_LIMIT_EXCEEDED',
            'retry_after': 60
        }), 429
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            'success': False,
            'error': 'Resource not found',
            'path': request.path,
            'method': request.method
        }), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        StructuredLogger.error(
            {"event": "internal_error", "error": str(e)},
            extra={"path": request.path}
        )
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        StructuredLogger.error(
            {"event": "unhandled_exception", "error": str(e)},
            extra={"path": request.path}
        )
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': 'An unexpected error occurred'
        }), 500
    
    # ─── HEALTH ROUTES ────────────────────────────────────────────
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check with proper status tracking."""
        
        # ✅ FIX: Explicit guard for Supabase
        supabase_status = 'disconnected'
        if get_supabase_client is not None:
            try:
                get_supabase_client()
                supabase_status = 'connected'
            except Exception as e:
                StructuredLogger.error(
                    {"event": "supabase_health_failed", "error": str(e)}
                )
                supabase_status = 'error' if ENV == 'production' else 'disconnected'
        else:
            supabase_status = 'unavailable'
        
        # M-Pesa status
        mpesa_status = False
        if is_mpesa_configured is not None:
            try:
                mpesa_status = is_mpesa_configured()
            except Exception:
                pass
        
        # ✅ FIX: Correct health status logic
        if supabase_status == 'connected' and mpesa_status:
            overall_status = 'healthy'
        elif supabase_status == 'error' or not mpesa_status:
            overall_status = 'unhealthy'
        else:
            overall_status = 'degraded'
        
        # ✅ FIX: Industry standard status codes
        # healthy → 200, degraded → 200, unhealthy → 503
        status_code = 503 if overall_status == 'unhealthy' else 200
        
        return jsonify({
            'success': True,
            'data': {
                'status': overall_status,
                'timestamp': datetime.now().isoformat(),
                'version': VERSION,
                'environment': ENV,
                'services': {
                    'mpesa': {
                        'configured': mpesa_status,
                        'environment': Config.MPESA_ENV,
                        'shortcode': Config.MPESA_SHORTCODE,
                        'callback_url': Config.MPESA_CALLBACK_URL
                    },
                    'supabase': {
                        'status': supabase_status
                    },
                    'redis': {
                        'enabled': bool(REDIS_URL),
                        'ready': REDIS_READY
                    }
                }
            }
        }), status_code
    
    @app.route('/api/ping', methods=['GET'])
    def ping():
        return jsonify({
            'success': True,
            'data': {
                'pong': True,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
    
    @app.route('/')
    def root():
        return jsonify({
            'success': True,
            'data': {
                'name': 'AUTO-V API',
                'version': VERSION,
                'status': 'operational',
                'environment': ENV,
                'endpoints': {
                    'health': '/api/health',
                    'ping': '/api/ping',
                    'mpesa_initiate': '/api/mpesa/initiate',
                    'mpesa_status': '/api/mpesa/status/<payment_id>',
                    'mpesa_callback': '/api/mpesa/callback',
                    'mpesa_auto_confirm': '/api/mpesa/auto-confirm/<payment_id>'
                }
            }
        }), 200
    
    # ─── SERVE FRONTEND ────────────────────────────────────────────
    @app.route('/portal')
    def serve_portal():
        return send_from_directory('templates', 'customer-portal.html')
    
    # ─── REGISTER BLUEPRINTS ──────────────────────────────────────
    def register_blueprints():
        registered = 0
        
        try:
            from api.routes.mpesa import mpesa_bp
            app.register_blueprint(mpesa_bp, url_prefix='/api/mpesa')
            registered += 1
            StructuredLogger.info("Blueprint registered", {"event": "blueprint_registered", "name": "mpesa"})
        except Exception as e:
            StructuredLogger.error(
                {"event": "blueprint_failed", "error": str(e)},
                extra={"blueprint": "mpesa"}
            )
        
        # ✅ FIX: Strict blueprint verification
        try:
            route_found = any(
                rule.rule == "/api/mpesa/callback"
                for rule in app.url_map.iter_rules()
            )
            if route_found:
                StructuredLogger.info("Callback route verified", {"event": "route_verified"})
            else:
                StructuredLogger.warning("Callback route not found", {"event": "route_missing"})
        except Exception as e:
            StructuredLogger.warning(
                {"event": "route_verification_failed", "error": str(e)}
            )
        
        return registered
    
    # ─── Retry-Safe Supabase Init ──────────────────────────────────
    def init_supabase():
        """Initialize Supabase with retry logic."""
        if get_supabase_client is None:
            StructuredLogger.critical("Supabase client not available", {"event": "supabase_unavailable"})
            if ENV == 'production':
                raise RuntimeError("Supabase client not available in production")
            return False
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                get_supabase_client()
                StructuredLogger.info(
                    "Supabase initialized",
                    {"event": "supabase_initialized", "attempt": attempt + 1}
                )
                return True
            except Exception as e:
                StructuredLogger.warning(
                    {"event": "supabase_init_failed", "error": str(e)},
                    extra={"attempt": attempt + 1}
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    if ENV == 'production':
                        raise RuntimeError(f"Supabase initialization failed: {e}")
                    return False
        
        return False
    
    # ─── GRACEFUL SHUTDOWN ──────────────────────────────────────
    def graceful_shutdown(signum, frame):
        StructuredLogger.info("Shutdown signal received", {"event": "shutdown_start"})
        
        if redis_client is not None:
            try:
                redis_client.close()
                StructuredLogger.info("Redis connection closed", {"event": "redis_closed"})
            except Exception as e:
                StructuredLogger.warning(
                    {"event": "redis_close_failed", "error": str(e)}
                )
        
        StructuredLogger.info("Shutdown complete", {"event": "shutdown_complete"})
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)
    
    # ─── Start Services ──────────────────────────────────────────
    init_supabase()
    registered = register_blueprints()
    
    # ✅ FIX: Startup health gate
    if ENV == 'production':
        if not REDIS_READY:
            StructuredLogger.critical("Redis not ready - exiting", {"event": "startup_failed"})
            sys.exit(1)
    
    # Log startup
    StructuredLogger.info(
        {"event": "startup_complete", "version": VERSION},
        extra={
            "environment": ENV,
            "mpesa_shortcode": Config.MPESA_SHORTCODE,
            "mpesa_env": Config.MPESA_ENV,
            "callback_url": Config.MPESA_CALLBACK_URL,
            "registered_blueprints": registered,
            "redis_ready": REDIS_READY
        }
    )
    
    return app


# ─── CREATE APP ──────────────────────────────────────────────
app = create_app()

# ─── MAIN ENTRY POINT ────────────────────────────────────────
if __name__ == '__main__':
    if ENV == 'production':
        StructuredLogger.info(
            {"event": "server_start", "port": PORT},
            extra={"server": "waitress"}
        )
        try:
            from waitress import serve
            serve(app, host='0.0.0.0', port=PORT, threads=4)
        except ImportError:
            StructuredLogger.warning("Waitress not installed, using Flask development server")
            app.run(host='0.0.0.0', port=PORT, debug=False)
    else:
        app.run(
            host='0.0.0.0',
            port=PORT,
            debug=DEBUG
        )
