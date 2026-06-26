"""
AUTO-V FastAPI Application Entry Point
Complete with all routes, middleware, and configuration
"""

import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import supabase
from app.routes import health, mpesa, valuation, certificates, vehicles, dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting AUTO-V API...")
    logger.info(f"📡 Environment: {settings.ENV}")
    logger.info(f"🔗 Database: {settings.SUPABASE_URL}")
    
    # Test Supabase connection
    try:
        await supabase.test_connection()
        logger.info("✅ Supabase connected successfully")
    except Exception as e:
        logger.error(f"❌ Supabase connection error: {e}")
    
    yield
    # Shutdown
    logger.info("🛑 Shutting down AUTO-V API...")


# Create FastAPI app
app = FastAPI(
    title="AUTO-V API",
    version=settings.APP_VERSION,
    description="AUTO-V Backend - M-Pesa + AI Valuation Engine + Certificate Generator",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "M-Pesa", "description": "M-Pesa payment integration"},
        {"name": "Valuation", "description": "AI-powered vehicle valuation"},
        {"name": "Certificates", "description": "Certificate generation and management"},
        {"name": "Vehicles", "description": "Vehicle management"},
        {"name": "Dashboard", "description": "Dashboard analytics"}
    ]
)

# Rate limit handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda req, exc: JSONResponse(
    status_code=429,
    content={
        "success": False,
        "error": "Rate limit exceeded",
        "message": str(exc)
    }
))

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to each request"""
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        import uuid
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and responses"""
    start_time = time.time()
    
    # Log request
    logger.info(f"📥 {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response
    duration = time.time() - start_time
    logger.info(f"📤 {response.status_code} {request.method} {request.url.path} - {duration:.3f}s")
    
    return response


# ─── Root and Health Endpoints ──────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "name": "AUTO-V API",
        "version": settings.APP_VERSION,
        "description": "Africa's Vehicle Intelligence Platform",
        "docs": "/docs",
        "status": "operational"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "timestamp": time.time()
    }


@app.get("/api/mpesa/test", tags=["M-Pesa"])
async def test_mpesa_callback():
    """Test endpoint for M-Pesa callback"""
    return {
        "status": "ok",
        "message": "M-Pesa callback endpoint is reachable",
        "callback_url": settings.MPESA_CALLBACK_URL,
        "base_url": settings.BASE_URL,
        "mpesa_configured": bool(
            settings.MPESA_CONSUMER_KEY and 
            settings.MPESA_CONSUMER_SECRET and 
            settings.MPESA_PASSKEY
        )
    }


# ─── Include Routers ──────────────────────────────────────

app.include_router(health.router)
app.include_router(mpesa.router)
app.include_router(valuation.router)
app.include_router(certificates.router)
app.include_router(vehicles.router)
app.include_router(dashboard.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
