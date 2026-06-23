# ============================================================
# CRITICAL SYSTEM FIX - MUST BE FIRST LINE IN APP ENTRYPOINT
# ============================================================

import os

# ─── PROXY HARD RESET (Production Grade - FINAL) ────────────
proxy_keys = [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy"
]

# Remove proxies completely - DO NOT set empty string
for k in proxy_keys:
    os.environ.pop(k, None)

# Hard guarantee: prevent HTTPX proxy resolution entirely
os.environ["NO_PROXY"] = "*"
os.environ.setdefault("SUPABASE_POSTGREST_CLIENT_TIMEOUT", "60")

# ============================================================
# NOW SAFE TO IMPORT EVERYTHING ELSE
# ============================================================

import logging
import json
import time
import uuid
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional
from contextlib import contextmanager

from flask import Flask, jsonify, request, g, has_request_context
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(override=True)

# ─── Structured JSON Logger ──────────────────────────────────
class StructuredLogger:
    """Production-grade JSON structured logger with request tracing."""
    
    @staticmethod
    def _get_request_id() -> str:
        if has_request_context():
            return getattr(g, 'request_id', 'no-request')
        return 'no-request'
    
    @staticmethod
    def _format_log(level: str, message: str, extra: Dict[str, Any] = None) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
            "request_id": StructuredLogger._get_request_id(),
            "environment": os.getenv("FLASK_ENV", "production"),
            "service": "auto-v",
            "version": os.getenv("APP_VERSION", "5.1.0")
        }
        if extra:
            log_entry.update(extra)
        return json.dumps(log_entry)
    
    @staticmethod
    def info(message: str, extra: Dict[str, Any] = None):
        print(StructuredLogger._format_log("INFO", message, extra))
    
    @staticmethod
    def warning(message: str, extra: Dict[str, Any] = None):
        print(StructuredLogger._format_log("WARNING", message, extra))
    
    @staticmethod
    def error(message: str, extra: Dict[str, Any] = None):
        print(StructuredLogger._format_log("ERROR", message, extra))
    
    @staticmethod
    def debug(message: str, extra: Dict[str, Any] = None):
        if os.getenv("FLASK_DEBUG", "false").lower() == "true":
            print(StructuredLogger._format_log("DEBUG", message, extra))
    
    @staticmethod
    def critical(message: str, extra: Dict[str, Any] = None):
        print(StructuredLogger._format_log("CRITICAL", message, extra))


logger = StructuredLogger()

# ─── Config Manager ──────────────────────────────────────────
class Config:
    """Centralized configuration management with environment overrides."""
    
    # Core
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    PORT = int(os.getenv("PORT", 10000))
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())
    APP_VERSION = os.getenv("APP_VERSION", "5.1.0")
    
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    SUPABASE_TIMEOUT = int(os.getenv("SUPABASE_POSTGREST_CLIENT_TIMEOUT", "60"))
    SUPABASE_MAX_RETRIES = int(os.getenv("SUPABASE_MAX_RETRIES", "3"))
    SUPABASE_RETRY_DELAY = int(os.getenv("SUPABASE_RETRY_DELAY", "2"))
    
    # M-Pesa
    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "4095377")
    MPESA_ENV = os.getenv("MPESA_ENV", "production")
    MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL")
    
    # CORS
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "200 per day,50 per hour")
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all config values for health checks."""
        return {
            "environment": cls.ENV,
            "version": cls.APP_VERSION,
            "debug": cls.DEBUG,
            "supabase_configured": bool(cls.SUPABASE_URL and cls.SUPABASE_ANON_KEY),
            "mpesa_configured": bool(cls.MPESA_CONSUMER_KEY and cls.MPESA_CONSUMER_SECRET),
            "redis_configured": bool(cls.REDIS_URL),
            "rate_limiting": cls.RATE_LIMIT_ENABLED
        }


# ─── Supabase Connection Wrapper (Singleton + Retry) ──────
class SupabaseConnection:
    """Production-grade Supabase connection with retry and fallback."""
    
    _instance = None
    _client = None
    _last_connected = None
    _connection_attempts = 0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_client(cls, retry: bool = True):
        """Get Supabase client with retry logic."""
        if cls._client is not None:
            return cls._client
        
        if not Config.SUPABASE_URL or not Config.SUPABASE_ANON_KEY:
            logger.error("Supabase credentials not configured")
            raise ValueError("Supabase credentials not configured")
        
        max_retries = Config.SUPABASE_MAX_RETRIES if retry else 1
        retry_delay = Config.SUPABASE_RETRY_DELAY
        
        for attempt in range(max_retries):
            try:
                from supabase import create_client, Client
                
                cls._client = create_client(
                    Config.SUPABASE_URL,
                    Config.SUPABASE_ANON_KEY
                )
                cls._last_connected = datetime.utcnow()
                cls._connection_attempts += 1
                
                # ✅ SAFE: Verify connection without crashing on missing table
                try:
                    cls._client.table('system_settings').select('*').limit(1).execute()
                    logger.info("Supabase connection verified")
                except Exception as e:
                    # Table might not exist yet - this is NOT critical
                    logger.warning(f"Supabase table verification skipped (non-critical): {e}")
                
                return cls._client
                
            except Exception as e:
                cls._client = None
                cls._connection_attempts += 1
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Supabase connection attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Supabase connection failed after {max_retries} attempts: {e}")
                    raise
    
    @classmethod
    def reset(cls):
        """Reset connection (useful for testing)."""
        cls._client = None
        cls._last_connected = None
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Get connection status for health checks."""
        return {
            "connected": cls._client is not None,
            "last_connected": cls._last_connected.isoformat() + "Z" if cls._last_connected else None,
            "attempts": cls._connection_attempts,
            "url_configured": bool(Config.SUPABASE_URL),
            "timeout": Config.SUPABASE_TIMEOUT
        }


# ─── Retry Decorator ────────────────────────────────────────
def with_retry(max_retries: int = 3, delay: int = 1, backoff: int = 2):
    """Decorator for retrying functions with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}): {e}. "
                            f"Retrying in {wait_time}s"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Function {func.__name__} failed after {max_retries} attempts: {e}")
                        raise
            raise last_error
        return wrapper
    return decorator


# ─── Middleware Registration ─────────────────────────────────
def register_middleware(app):
    """Register request/response middleware safely (prevents duplicate registration)."""
    
    @app.before_request
    def before_request():
        """Add request ID and start time to request context."""
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])
        g.start_time = time.time()
        
        logger.info(
            f"Request started: {request.method} {request.path}",
            {
                "method": request.method,
                "path": request.path,
                "client_ip": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', 'unknown')
            }
        )

    @app.after_request
    def after_request(response):
        """Add request ID to response and log completion."""
        if has_request_context() and hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
            
            duration = time.time() - g.start_time if hasattr(g, 'start_time') else 0
            logger.info(
                f"Request completed: {request.method} {request.path}",
                {
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": g.request_id
                }
            )
            
            # Log slow requests (>1 second)
            if duration > 1.0:
                logger.warning(
                    f"Slow request: {duration:.2f}s",
                    {
                        "path": request.path,
                        "duration": duration,
                        "status": response.status_code,
                        "request_id": g.request_id
                    }
                )
        
        return response


# ─── App Factory ─────────────────────────────────────────────
def create_app():
    """Application factory with all features initialized."""
    
    # ─── Configure Flask ──────────────────────────────────────────
    app = Flask(__name__)
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['JSON_SORT_KEYS'] = False
    
    # ─── CORS ──────────────────────────────────────────────────────
    CORS(
        app,
        resources={r"/*": {"origins": Config.ALLOWED_ORIGINS}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-Session-Token", "Accept", "X-Request-ID"],
        expose_headers=["Content-Type", "Authorization", "X-Request-ID"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        max_age=3600
    )
    
    # ─── REGISTER MIDDLEWARE (Safe, no duplicate risk) ───────────
    register_middleware(app)
    
    # ─── ERROR HANDLERS ──────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"Not found: {request.path}")
        return jsonify({
            "success": False,
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": request.path,
            "request_id": getattr(g, 'request_id', None)
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        logger.warning(f"Method not allowed: {request.method} {request.path}")
        return jsonify({
            "success": False,
            "error": "Method Not Allowed",
            "message": f"Method {request.method} is not allowed for this endpoint",
            "request_id": getattr(g, 'request_id', None)
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}", {"error": str(error)})
        return jsonify({
            "success": False,
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": getattr(g, 'request_id', None)
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error(f"Unhandled exception: {error}", {"error": str(error)})
        return jsonify({
            "success": False,
            "error": "Server Error",
            "message": "An unexpected error occurred",
            "request_id": getattr(g, 'request_id', None)
        }), 500
    
    # ─── REGISTER BLUEPRINTS ──────────────────────────────────────
    try:
        from api.routes.mpesa import mpesa_bp
        app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")
        logger.info("M-Pesa blueprint registered successfully")
    except ImportError as e:
        logger.error(f"Failed to import M-Pesa blueprint: {e}")
    except Exception as e:
        logger.error(f"M-Pesa blueprint failed to load: {e}")
    
    # ─── PREFLIGHT HANDLER ──────────────────────────────────────
    @app.route("/<path:path>", methods=["OPTIONS"])
    def options_handler(path):
        return jsonify({"status": "ok"}), 200
    
    # ─── ROUTES ──────────────────────────────────────────────────
    @app.route("/", methods=["GET"])
    def home():
        return jsonify({
            "success": True,
            "data": {
                "name": "AUTO-V API",
                "version": Config.APP_VERSION,
                "environment": Config.ENV,
                "status": "operational",
                "endpoints": {
                    "health": "/api/health",
                    "ping": "/api/ping",
                    "mpesa_initiate": "/api/mpesa/initiate",
                    "mpesa_status": "/api/mpesa/status/<payment_id>",
                    "mpesa_callback": "/api/mpesa/callback",
                    "mpesa_auto_confirm": "/api/mpesa/auto-confirm/<payment_id>"
                }
            }
        }), 200
    
    @app.route("/api/health", methods=["GET"])
    def health():
        """Comprehensive health check with all services."""
        return jsonify({
            "success": True,
            "data": {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": Config.APP_VERSION,
                "environment": Config.ENV,
                "config": Config.get_all(),
                "supabase": SupabaseConnection.get_status(),
                "mpesa": {
                    "configured": bool(
                        Config.MPESA_CONSUMER_KEY and 
                        Config.MPESA_CONSUMER_SECRET and 
                        Config.MPESA_PASSKEY
                    ),
                    "environment": Config.MPESA_ENV,
                    "shortcode": Config.MPESA_SHORTCODE,
                    "callback_url": Config.MPESA_CALLBACK_URL
                },
                "proxy": {
                    "HTTP_PROXY": "cleared" if os.getenv("HTTP_PROXY") is None else "set",
                    "HTTPS_PROXY": "cleared" if os.getenv("HTTPS_PROXY") is None else "set",
                    "NO_PROXY": os.getenv("NO_PROXY", "not set")
                },
                "redis": {
                    "configured": bool(Config.REDIS_URL)
                }
            }
        }), 200
    
    @app.route("/api/ping", methods=["GET"])
    def ping():
        return jsonify({
            "success": True,
            "data": {
                "pong": True,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }), 200
    
    return app


# ─── Gunicorn Entry Point ────────────────────────────────────
app = create_app()

# ─── Main Entry Point ────────────────────────────────────────
if __name__ == "__main__":
    logger.info(
        f"🚀 AUTO-V starting on port {Config.PORT}",
        {
            "environment": Config.ENV,
            "version": Config.APP_VERSION,
            "port": Config.PORT
        }
    )
    
    # Show configuration status
    logger.info("Configuration summary", {
        "supabase": "configured" if Config.SUPABASE_URL else "missing",
        "mpesa": "configured" if Config.MPESA_CONSUMER_KEY else "missing",
        "redis": "configured" if Config.REDIS_URL else "not configured",
        "proxy_cleared": os.getenv("HTTP_PROXY") is None
    })
    
    # Run with Waitress or Flask dev server
    if Config.ENV == "production":
        try:
            from waitress import serve
            logger.info(f"Starting Waitress server on port {Config.PORT}")
            serve(app, host="0.0.0.0", port=Config.PORT, threads=4, channel_timeout=300)
        except ImportError:
            logger.warning("Waitress not installed, using Flask development server")
            app.run(host="0.0.0.0", port=Config.PORT, debug=False)
    else:
        app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
