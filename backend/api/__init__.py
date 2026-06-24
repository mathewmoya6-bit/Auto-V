# ============================================================
# API Package Initialization
# ============================================================

from fastapi import APIRouter

# Create main API router
router = APIRouter(prefix="/api")

# Import route modules
from api.routes import mpesa

# Register routers
router.include_router(mpesa.router, prefix="/mpesa", tags=["M-Pesa"])

__all__ = ["router"]
