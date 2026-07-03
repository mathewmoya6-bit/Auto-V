# app/middleware/security.py
# =============================================================================
# SECURITY HEADERS MIDDLEWARE - Add security headers to all responses
# =============================================================================

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import settings


def setup_security_headers(app: FastAPI):
    """
    Add security headers middleware to the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        """Add security headers to every response."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (only in production)
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy (customize as needed)
        # response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


def setup_trusted_hosts(app: FastAPI):
    """
    Configure Trusted Host middleware for security.
    
    Args:
        app: FastAPI application instance
    """
    allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', ["*"])
    if not allowed_hosts or allowed_hosts == []:
        allowed_hosts = ["*"]
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts,
    )
    
    return app
