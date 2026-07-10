from .auth import router as auth_router
from .users import router as users_router
from .categories import router as categories_router
from .vehicles import router as vehicles_router
from .mileage import router as mileage_router
from .valuations import router as valuations_router
from .payments import router as payments_router
from .inspections import router as inspections_router
from .reports import router as reports_router
from .settings import router as settings_router

__all__ = [
    "auth_router",
    "users_router",
    "categories_router",
    "vehicles_router",
    "mileage_router",
    "valuations_router",
    "payments_router",
    "inspections_router",
    "reports_router",
    "settings_router"
]
