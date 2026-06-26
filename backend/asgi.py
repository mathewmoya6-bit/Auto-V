# ============================================================
# asgi.py - ASGI Entry Point
# For Uvicorn/Daphne/Starlette
# ============================================================

import os
import sys
from dotenv import load_dotenv

# ─── Load Environment ──────────────────────────────────────────
load_dotenv()

# ─── Add Backend to Path ──────────────────────────────────────
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# ─── Import Application ────────────────────────────────────────
try:
    from app.main import app as application
except ImportError as e:
    print(f"❌ Failed to import app: {e}")
    raise

# ─── Export for ASGI Servers ──────────────────────────────────
app = application

# ─── Startup Info ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AUTO-V API ASGI Server")
    print("=" * 60)
    print("📡 Running with Uvicorn")
    print("📡 API Docs: /docs")
    print("📡 Health: /health")
    print("=" * 60)
    
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(
        "asgi:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv('DEBUG', 'false').lower() == 'true',
        workers=int(os.getenv('WORKERS', 4)),
    )
