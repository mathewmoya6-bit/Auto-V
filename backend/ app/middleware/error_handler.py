# app/middleware/error_handler.py
# =============================================================================
# ERROR HANDLER MIDDLEWARE - Global exception handling
# =============================================================================

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.middleware.request_id import get_request_id

logger = get_logger(__name__)


def setup_error_handlers(app: FastAPI):
    """
    Register global exception handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        request_id = get_request_id(request)
        
        logger.warning(
            f"HTTP exception: {exc.status_code} - {exc.detail}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path,
                "request_id": request_id,
                "timestamp": str(datetime.now()),
            },
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        request_id = get_request_id(request)
        
        logger.warning(
            f"Validation error: {exc.errors()}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": exc.errors(),
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "path": request.url.path,
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unhandled exceptions."""
        request_id = get_request_id(request)
        
        logger.error(
            f"Unhandled exception: {str(exc)}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "path": request.url.path,
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id} if request_id else {},
        )


from datetime import datetime
