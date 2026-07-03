# app/middleware/__init__.py
# =============================================================================
# MIDDLEWARE - Complete middleware setup for FastAPI
# =============================================================================

from fastapi import FastAPI
from app.core.config import settings

from app.middleware.cors import setup_cors
from app.middleware.security import setup_security_headers, setup_trusted_hosts
from app.middleware.timing import setup_timing_middleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.error_handler import setup_error_handlers
from app.middleware.auth import AuthMiddleware


def setup_middleware(app: FastAPI):
    """
    Configure all middleware for the FastAPI application.
    Order matters - middleware runs in reverse order of registration.
    
    Args:
        app: FastAPI application instance
    """
    
    # 1. Error handlers (should run first)
    setup_error_handlers(app)
    
    # 2. Request ID (generates unique ID for tracing)
    app.add_middleware(RequestIDMiddleware)
    
    # 3. Logging (logs all requests)
    app.add_middleware(
        LoggingMiddleware,
        log_headers=settings.DEBUG,
        log_body=settings.DEBUG,
    )
    
    # 4. Rate Limiting
    app.add_middleware(
        RateLimitMiddleware,
        rate_limit=getattr(settings, 'RATELIMIT_DEFAULT', 100),
        window_seconds=60,
    )
    
    # 5. Authentication
    app.add_middleware(AuthMiddleware)
    
    # 6. CORS
    setup_cors(app)
    
    # 7. Security Headers
    setup_security_headers(app)
    
    # 8. Trusted Hosts
    if settings.is_production():
        setup_trusted_hosts(app)
    
    # 9. Timing
    setup_timing_middleware(app)
    
    return app


# Export individual middleware for direct use
__all__ = [
    "setup_middleware",
    "RequestIDMiddleware",
    "LoggingMiddleware",
    "RateLimitMiddleware",
    "AuthMiddleware",
    "setup_cors",
    "setup_security_headers",
    "setup_trusted_hosts",
    "setup_timing_middleware",
    "setup_error_handlers",
]
