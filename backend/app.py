# app.py - FIXED (No proxy)

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# ─── Load environment ──────────────────────────────────────────
load_dotenv()

# ─── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── Create Flask App ──────────────────────────────────────────
app = Flask(__name__)

# ─── CORS ──────────────────────────────────────────────────────
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://auto-v.meipressgroup.com",
            "https://auto-v.onrender.com",
            "https://auto-v-backend.onrender.com",
            "http://localhost:3000",
            "http://localhost:5000"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Session-Token"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

# ─── Configuration ─────────────────────────────────────────────
class Config:
    """Application configuration."""
    
    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://tsvejnzxrxrrecgquxbq.supabase.co')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
    SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET', '')
    
    # M-Pesa
    MPESA_ENV = os.getenv('MPESA_ENV', 'production')
    MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
    MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
    MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
    MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
    MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', '')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(24).hex())
    
    # Environment
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

app.config.from_object(Config)

# ─── IMPORTANT: Fix Supabase client - NO proxy ────────────────
# Override any proxy settings that might be set
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

# ─── Register Routes ────────────────────────────────────────────
def register_blueprints():
    """Register all blueprints."""
    try:
        # ─── M-Pesa Routes ──────────────────────────────────
        from api.routes.mpesa import mpesa_bp
        app.register_blueprint(mpesa_bp, url_prefix='/api/mpesa')
        logger.info("✅ M-Pesa routes registered")
        
        # ─── Auth Routes ────────────────────────────────────
        try:
            from api.routes.auth import auth_bp
            app.register_blueprint(auth_bp, url_prefix='/api/auth')
            logger.info("✅ Auth routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ Auth routes not found: {e}")
        
        # ─── Admin Routes ──────────────────────────────────
        try:
            from api.routes.admin import admin_bp
            app.register_blueprint(admin_bp, url_prefix='/api/admin')
            logger.info("✅ Admin routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ Admin routes not found: {e}")
            
    except Exception as e:
        logger.error(f"❌ Failed to register blueprints: {e}")
        raise

# ─── Health Check ──────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'environment': app.config['ENV'],
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/ping', methods=['GET'])
def ping():
    """Simple ping endpoint."""
    return jsonify({'pong': True, 'timestamp': datetime.now().isoformat()}), 200

@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'name': 'AUTO-V API',
        'version': '2.0.0',
        'environment': app.config['ENV'],
        'status': 'operational'
    }), 200

# ─── Error Handlers ────────────────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found', 'path': request.path}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# ─── Initialize App ────────────────────────────────────────────
register_blueprints()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    
    # ─── CRITICAL: Ensure no proxy before starting ──────────────
    # Remove any proxy environment variables
    for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        if proxy_var in os.environ:
            del os.environ[proxy_var]
            logger.info(f"✅ Removed {proxy_var} environment variable")
    
    if app.config['ENV'] == 'production':
        logger.info(f"🚀 Starting production server on port {port}")
        from waitress import serve
        serve(app, host='0.0.0.0', port=port, threads=4)
    else:
        app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
