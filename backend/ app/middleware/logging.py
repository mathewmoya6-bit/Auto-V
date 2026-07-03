# app/middleware/logging.py
# =============================================================================
# LOGGING MIDDLEWARE - Request/response logging with structured logs
# =============================================================================

import time
import json
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger
from app.middleware.request_id import get_request_id

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests with timing and metadata.
    Uses structured JSON logging for production.
    """

    def __init__(self, app: ASGIApp, log_headers: bool = False, log_body: bool = False):
        super().__init__(app)
        self.log_headers = log_headers
        self.log_body = log_body

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = get_request_id(request)
        
        # Log request
        await self.log_request(request, request_id)
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        await self.log_response(request, response, duration, request_id)
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response

    async def log_request(self, request: Request, request_id: Optional[str]):
        """Log incoming request details."""
        log_data = {
            "event": "request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        }
        
        if self.log_headers:
            log_data["headers"] = dict(request.headers)
        
        logger.info(json.dumps(log_data))

    async def log_response(self, request: Request, response: Response, duration: float, request_id: Optional[str]):
        """Log response details with timing."""
        log_data = {
            "event": "response",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "client_ip": request.client.host if request.client else "unknown",
        }
        
        logger.info(json.dumps(log_data))
