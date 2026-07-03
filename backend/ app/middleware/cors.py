# app/middleware/cors.py
# =============================================================================
# CORS MIDDLEWARE - Custom CORS handling with preflight caching
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware
from app.core.config import settings


def setup_cors(app: FastAPI):
    """
    Configure CORS middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Get CORS origins with fallback
    cors_origins = getattr(settings, 'CORS_ORIGINS', ["*"])
    if not cors_origins or cors_origins == []:
        cors_origins = ["*"]
    
    app.add_middleware(
        FastAPICORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "X-Request-ID",
            "X-Requested-With",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Response-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        max_age=3600,  # Cache preflight request for 1 hour
    )
    
    return app
