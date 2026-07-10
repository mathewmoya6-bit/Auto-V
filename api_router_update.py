# app/api/v1/api.py  (EXCERPT — add to your existing file, don't overwrite it)
#
# Your api.py presumably already looks like this for the existing 9 modules:
#
#   from fastapi import APIRouter
#   from app.api.v1.endpoints import (
#       auth, users, categories, vehicles, mileage,
#       valuation, payments, inspections, reports,
#   )
#
#   api_router = APIRouter()
#   api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
#   api_router.include_router(users.router, prefix="/users", tags=["Users"])
#   ...
#   api_router.include_router(inspections.router, tags=["Inspections"])  # no prefix,
#       # since inspections.router already declares full paths like
#       # "/vehicles/{vehicle_id}/inspections" and "/inspections/{inspection_id}"
#
# Add these for the new modules:

from app.api.v1.endpoints import instant_value, vehicle_assessments  # noqa: E402

api_router.include_router(
    instant_value.router, prefix="/instant-value", tags=["Instant Value"]
)
api_router.include_router(
    vehicle_assessments.router, tags=["Vehicle Assessments"]  # no prefix — see note
)

# Resulting new paths (given settings.api_v1_prefix == "/api/v1"):
#   POST /api/v1/instant-value/estimate
#   GET  /api/v1/instant-value/estimate/{estimate_id}
#   GET  /api/v1/instant-value/history
#   POST /api/v1/vehicles/{vehicle_id}/assessments
#   GET  /api/v1/vehicles/{vehicle_id}/assessments
#   GET  /api/v1/assessments/{assessment_id}
#   GET  /api/v1/assessments/{assessment_id}/report
#
# vehicle_assessments has no prefix (same pattern as your Inspections and
# Mileage modules) because its own paths already mix "/vehicles/{id}/..."
# and "/assessments/{id}" — adding a prefix would double one of those up.
