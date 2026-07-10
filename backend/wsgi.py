# ============================================================
# wsgi.py - Production WSGI Entry Point
# FastAPI version for Gunicorn/Uvicorn
# ============================================================

import os
import sys
import logging
from dotenv import load_dotenv

# ─── Load Environment ──────────────────────────────────────────
load_dotenv()

# ─── Add Backend to Path ──────────────────────────────────────
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# ─── Configure Logging ─────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ─── Supress Uvicorn Access Logs in Production ────────────────
if os.getenv('ENV', 'production') == 'production':
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)

# ─── Import FastAPI App ────────────────────────────────────────
try:
    from app.main import app as application
    logger.info("✅ FastAPI application loaded successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import FastAPI app: {e}")
    raise

# ─── For Gunicorn/Uvicorn ─────────────────────────────────────
app = application

# ─── Health Check for Load Balancers ──────────────────────────
@app.get("/health/lb")
async def load_balancer_health():
    """Lightweight health check for load balancers."""
    return {"status": "healthy", "service": "auto-v-api"}


# ─── Startup Info ──────────────────────────────────────────────
def print_startup_info():
    """Print startup information."""
    env = os.getenv('ENV', 'production')
    port = os.getenv('PORT', 8000)
    mpesa_shortcode = os.getenv('MPESA_SHORTCODE', 'N/A')
    
    print("=" * 60)
    print("🚀 AUTO-V API Production Server (FastAPI)")
    print("=" * 60)
    print(f"📡 Environment: {env}")
    print(f"📡 Port: {port}")
    print(f"📡 Workers: {os.getenv('WORKERS', '4')}")
    print(f"🔑 M-Pesa Shortcode: {mpesa_shortcode}")
    print(f"📦 Version: {os.getenv('APP_VERSION', '2.0.0')}")
    print(f"📋 Routes registered:")
    print("   - /docs (OpenAPI)")
    print("   - /redoc (ReDoc)")
    print("   - /health")
    print("   - /api/v1/*")
    print("=" * 60)


# ─── Main Entry Point ──────────────────────────────────────────
if __name__ == "__main__":
    print_startup_info()
    
    # Check for required environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SECRET_KEY']
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.warning(f"⚠️ Missing environment variables: {', '.join(missing)}")
    
    # Run with uvicorn
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    uvicorn.run(
        "wsgi:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
        workers=1 if debug else int(os.getenv('WORKERS', 4)),
        log_level="info" if debug else "warning",
        loop="uvloop",
        http="httptools",
        lifespan="on",
    )
