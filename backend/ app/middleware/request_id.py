# app/middleware/request_id.py
# =============================================================================
# REQUEST ID MIDDLEWARE - Generate unique request IDs for tracing
# =============================================================================

import uuid
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates a unique request ID for each request.
    Adds the ID to the response headers and makes it available in the request state.
    """

    def __init__(self, app: ASGIApp, header_name: str = REQUEST_ID_HEADER):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store in request state for later use
        request.state.request_id = request_id
        
        # Add to response headers
        response = await call_next(request)
        response.headers[self.header_name] = request_id
        
        # Log request ID
        logger.debug(f"Request ID: {request_id} - {request.method} {request.url.path}")
        
        return response


def get_request_id(request: Request) -> Optional[str]:
    """Helper to get the current request ID from request state."""
    return getattr(request.state, "request_id", None)
