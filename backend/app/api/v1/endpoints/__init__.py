from .auth import router as auth_router
from .users import router as users_router
from .categories import router as categories_router
from .vehicles import router as vehicles_router
from .mileage import router as mileage_router
from .instant_value import router as instant_value_router
from .vehicle_assessments import router as vehicle_assessments_router
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
    "instant_value_router",
    "vehicle_assessments_router",
    "valuations_router",
    "payments_router",
    "inspections_router",
    "reports_router",
    "settings_router"
]
