# api/__init__.py – AUTO-V FastAPI Application (Production-Ready)

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import routers
from api.routes.valuation import router as valuation_router
from api.routes.mileage import router as mileage_router
from api.routes.mpesa import router as mpesa_router
from api.routes.payments import router as payments_router
from api.routes.assessment import router as assessment_router
from api.routes.inspection import router as inspection_router
from api.routes.instant import router as instant_router
from api.routes.admin import router as admin_router
from api.routes.auth import router as auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================
# RATE LIMITING (Prevent abuse)
# ============================================================
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="AUTO-V API",
    description="Africa's Vehicle Intelligence Platform – Professional Valuation, Inspection, Assessment & Mileage",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================================
# CORS (Configure for production)
# ============================================================
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# GLOBAL EXCEPTION HANDLERS
# ============================================================
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "error", "message": "Validation error", "details": exc.errors()},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "message": "Internal server error"},
    )

# ============================================================
# HEALTH CHECK & ROOT
# ============================================================
@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    return {
        "status": "AUTO-V API running",
        "version": "2.0.0",
        "timestamp": "online",
        "docs": "/docs",
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ============================================================
# REGISTER ROUTERS
# ============================================================
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(instant_router, prefix="/api/instant", tags=["Instant Value"])
app.include_router(valuation_router, prefix="/api/valuation", tags=["Valuation"])
app.include_router(inspection_router, prefix="/api/inspection", tags=["Inspection"])
app.include_router(assessment_router, prefix="/api/assessment", tags=["Assessment"])
app.include_router(mileage_router, prefix="/api/mileage", tags=["Mileage"])
app.include_router(mpesa_router, prefix="/api/mpesa", tags=["M-Pesa"])
app.include_router(payments_router, prefix="/api/payments", tags=["Payments"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])

# ============================================================
# LIFECYCLE EVENTS (OPTIONAL)
# ============================================================
@app.on_event("startup")
async def startup_event():
    logger.info("AUTO-V API starting up...")
    # Initialize any connections, e.g., Supabase, Redis, etc.

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("AUTO-V API shutting down...")
    # Clean up resources

# ============================================================
# HELPER: IMPORT os, datetime for use in the module
# ============================================================
import os
from datetime import datetime

# ============================================================
# RUN (for local development)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
