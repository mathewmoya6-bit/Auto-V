# ============================================================
# run.py - FastAPI Startup Script
# ============================================================

import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    print("=" * 60)
    print("🚀 AUTO-V FastAPI Server")
    print("=" * 60)
    print(f"📡 Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"📡 Port: {port}")
    print(f"📡 Debug: {debug}")
    print(f"📡 API Docs: http://localhost:{port}/api/docs")
    print(f"📡 Health: http://localhost:{port}/api/health")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
        log_level="info"
    )
