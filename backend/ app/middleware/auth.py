# app/middleware/auth.py
# =============================================================================
# AUTH MIDDLEWARE - JWT authentication and authorization
# =============================================================================

from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger
from app.core.deps import get_current_user

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles JWT authentication for protected routes.
    Skips authentication for public endpoints.
    """

    def __init__(
        self,
        app: ASGIApp,
        public_paths: Optional[List[str]] = None,
        admin_only_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.public_paths = public_paths or [
            "/health",
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/verify",
            "/api/webhooks/mpesa",
        ]
        self.admin_only_paths = admin_only_paths or [
            "/api/v1/admin",
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        if any(request.url.path.startswith(path) for path in self.public_paths):
            return await call_next(request)

        # Check for admin-only paths
        is_admin_route = any(request.url.path.startswith(path) for path in self.admin_only_paths)
        
        try:
            # Get current user
            user = await get_current_user(request)
            
            # Store user in request state
            request.state.user = user
            
            # Check admin access if needed
            if is_admin_route and user.role not in ["admin", "super_admin"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )
                
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.warning(f"Auth error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
