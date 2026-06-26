# ============================================================
# run.py - FastAPI Startup Script
# Production Ready with Full Configuration
# ============================================================

import os
import sys
import logging
import uvicorn
from dotenv import load_dotenv

# ─── Load Environment ──────────────────────────────────────────
load_dotenv()

# ─── Configure Logging ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner(port: int, debug: bool, env: str):
    """Print startup banner."""
    banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   🚀  AUTO-V FastAPI Server                                     ║
║   ═══════════════════════════════                               ║
║                                                                  ║
║   📡 Environment: {env:<10}                                      ║
║   📡 Port:        {port:<6}                                      ║
║   📡 Debug:       {str(debug):<6}                                ║
║   📡 API Docs:    http://localhost:{port}/docs                  ║
║   📡 ReDoc:       http://localhost:{port}/redoc                 ║
║   📡 Health:      http://localhost:{port}/health                ║
║                                                                  ║
║   🛑 Press Ctrl+C to stop                                       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_environment():
    """Check required environment variables."""
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SECRET_KEY',
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.warning(f"⚠️ Missing environment variables: {', '.join(missing)}")
        logger.warning("⚠️ Some features may not work properly")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True


def check_supabase():
    """Check Supabase connection on startup."""
    try:
        from app.core.database import check_supabase_health
        status = check_supabase_health()
        
        if status.get('connected'):
            logger.info("✅ Supabase connected successfully")
        else:
            logger.warning(f"⚠️ Supabase connection issue: {status.get('error')}")
        return status
    except Exception as e:
        logger.error(f"❌ Supabase check failed: {e}")
        return None


def get_uvicorn_config(debug: bool) -> dict:
    """Get uvicorn configuration."""
    config = {
        "app": "app.main:app",
        "host": "0.0.0.0",
        "port": int(os.getenv("PORT", 8000)),
        "reload": debug,
        "log_level": "debug" if debug else "info",
        "access_log": True,
        "use_colors": True,
        "workers": 1 if debug else int(os.getenv("WORKERS", 4)),
        "loop": "uvloop",
        "http": "httptools",
        "lifespan": "on",
        "timeout_keep_alive": 60,
        "timeout_graceful_shutdown": 30,
    }
    
    # Add SSL if configured
    if os.getenv("SSL_ENABLED", "false").lower() == "true":
        config["ssl_keyfile"] = os.getenv("SSL_KEY_PATH")
        config["ssl_certfile"] = os.getenv("SSL_CERT_PATH")
    
    return config


def main():
    """Main entry point."""
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="AUTO-V FastAPI Server")
    parser.add_argument("--port", type=int, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--workers", type=int, help="Number of workers")
    parser.add_argument("--env-file", type=str, help="Environment file path")
    args = parser.parse_args()
    
    # Load environment from file if specified
    if args.env_file:
        load_dotenv(args.env_file)
    
    # Get configuration
    port = args.port or int(os.getenv("PORT", 8000))
    debug = args.debug or os.getenv("DEBUG", "false").lower() == "true"
    env = os.getenv("ENV", "development")
    workers = args.workers or int(os.getenv("WORKERS", 4))
    
    # Print banner
    print_banner(port, debug, env)
    
    # Check environment
    check_environment()
    
    # Check Supabase
    check_supabase()
    
    # Set environment for workers
    os.environ["ENV"] = env
    os.environ["DEBUG"] = str(debug).lower()
    
    # Run server
    try:
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=port,
            reload=debug,
            log_level="debug" if debug else "info",
            workers=1 if debug else workers,
            loop="uvloop",
            http="httptools",
            lifespan="on",
            timeout_keep_alive=60,
            timeout_graceful_shutdown=30,
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)


# ─── Alternative: Simple Startup ──────────────────────────────

def run_simple():
    """Simple startup without arguments."""
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    env = os.getenv("ENV", "development")
    
    print_banner(port, debug, env)
    check_environment()
    check_supabase()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
        log_level="debug" if debug else "info",
        workers=1 if debug else int(os.getenv("WORKERS", 4)),
    )


# ─── Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    main()
