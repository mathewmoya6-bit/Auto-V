# app/api/v1/endpoints/calculate.py
# =============================================================================
# AUTO-V API - Mileage Calculation Engine (v2)
#
# Mounted in api.py as:
#   api_router.include_router(calculate.router, prefix="/calculate", tags=[...])
# so routes below are RELATIVE ("/mileage", not "/calculate/mileage").
#
# Internal fields are snake_case (Python convention); the wire format is
# camelCase via the alias generator below, matching what the frontend
# already expects (totalCost, fixedRate, etc.) without forcing camelCase
# into the Python code itself.
# =============================================================================

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.mileage import VehicleCategory, VehicleVariant

logger = logging.getLogger(__name__)
router = APIRouter()

CALCULATION_VERSION = "2.0"


# =============================================================================
# camelCase-over-the-wire helper
# =============================================================================

def _to_camel(snake: str) -> str:
    head, *tail = snake.split("_")
    return head + "".join(part.title() for part in tail)


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


# =============================================================================
# Request / Response contracts
# =============================================================================

class MileageRequest(_CamelModel):
    """Request body for POST /calculate/mileage."""

    variant_id: UUID = Field(..., description="vehicle_variants.id to price out")
    distance: float = Field(..., gt=0, le=100_000, description="Trip distance in kilometers")
    include_forecast: bool = Field(False, description="Include 5-year cost forecast at this distance")
    include_comparison: bool = Field(False, description="Include fuel-type average comparison")

    @field_validator("distance")
    @classmethod
    def distance_must_be_finite(cls, v: float) -> float:
        if v != v or v in (float("inf"), float("-inf")):  # NaN / inf guard
            raise ValueError("distance must be a finite number")
        return v


class MileageResponse(_CamelModel):
    """Response body for POST /calculate/mileage. Field names are snake_case
    here; they serialize as camelCase (totalCost, fixedRate, ...) to match
    the frontend, since response_model_by_alias defaults to True in FastAPI."""

    currency: str = "KES"
    calculation_version: str = CALCULATION_VERSION

    total_cost: float
    fixed_cost: float
    operating_cost: float
    total_rate: float
    fixed_rate: float
    operating_rate: float
    components: Dict[str, float] = Field(default_factory=dict)
    yearly: Dict[str, float] = Field(default_factory=dict)
    initial_cost: float
    method: str
    distance: float
    forecast: Optional[Dict[str, float]] = None
    comparison: Optional[Dict[str, Any]] = None


# =============================================================================
# Reference data
#
# Both of these are reasonable as in-code constants for an MVP, but are
# structured as swappable single functions so moving them into Supabase
# later (see SQL below) is a one-function change, not a rewrite.
#
# Suggested migration when ready to make these data-driven per-country:
#
#   CREATE TABLE fuel_type_benchmarks (
#       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#       fuel_type TEXT NOT NULL,
#       country TEXT NOT NULL DEFAULT 'KE',
#       average_rate NUMERIC(10,4) NOT NULL,
#       effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
#       UNIQUE (fuel_type, country, effective_date)
#   );
#
#   CREATE TABLE calculation_history (
#       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#       user_id UUID REFERENCES users(id) ON DELETE SET NULL,
#       variant_id UUID NOT NULL REFERENCES vehicle_variants(id),
#       distance NUMERIC(10,2) NOT NULL,
#       result_json JSONB NOT NULL,
#       calculation_version TEXT NOT NULL,
#       created_at TIMESTAMPTZ NOT NULL DEFAULT now()
#   );
#
# Neither table is created automatically by this file -- run the SQL
# yourself when you're ready to make these data-driven / add history.
# =============================================================================

_FUEL_TYPE_AVERAGE_RATE = {
    "Petrol": 45.00,
    "Diesel": 52.00,
    "Electric": 30.00,
    "LPG": 38.00,
}
_DEFAULT_AVERAGE_RATE = 45.00


def _get_fuel_type_average_rate(fuel_type: str) -> float:
    """Swap this for a DB lookup against fuel_type_benchmarks once that
    table exists; signature deliberately takes only what it needs so the
    call site below doesn't have to change when this becomes async/DB-backed."""
    return _FUEL_TYPE_AVERAGE_RATE.get(fuel_type, _DEFAULT_AVERAGE_RATE)


# Annual inflation assumption per cost component, used only for the
# bottom-up fallback forecast (see _forecast). These are still reference
# assumptions, not measured data -- revisit when real historical cost
# data is available.
_COMPONENT_ANNUAL_INFLATION = {
    "Fuel": 0.06,
    "Repairs": 0.05,
    "Servicing": 0.04,
    "Tyres": 0.04,
    "Insurance": 0.03,
    "Licences": 0.02,
    "Depreciation": 0.00,
    "Interest": 0.00,
}
_DEFAULT_COMPONENT_INFLATION = 0.03

# A stored per-km rate above this is almost certainly bad data (typo,
# wrong unit, migration error) rather than a real value.
_MAX_PLAUSIBLE_RATE_PER_KM = 10_000.0


# =============================================================================
# Optional (non-blocking) auth
#
# Public callers work with no token at all. If a valid bearer token IS
# present, we attach the subject for logging/future calculation_history
# use -- this endpoint never requires auth, it just uses it when offered.
# =============================================================================

_optional_bearer = HTTPBearer(auto_error=False)


async def _optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
) -> Optional[str]:
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    return payload.get("sub")


# =============================================================================
# Endpoint
# =============================================================================

@router.post(
    "/mileage",
    response_model=MileageResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate trip cost for a vehicle variant",
    responses={
        404: {"description": "Vehicle variant not found or inactive"},
        422: {"description": "Invalid request body (bad UUID, non-positive distance, etc.)"},
        500: {"description": "Vehicle rate data failed a sanity check (see logs)"},
        503: {"description": "Database temporarily unavailable"},
    },
)
async def calculate_mileage(
    request: MileageRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Depends(_optional_user_id),
) -> MileageResponse:
    """
    Price out a trip for a specific vehicle variant.

    Public endpoint -- works anonymously. If called with a valid bearer
    token, the calling user is logged (and available for a future
    calculation_history feature) but is never required.
    """
    try:
        result = await db.execute(
            select(VehicleVariant, VehicleCategory)
            .join(VehicleCategory, VehicleVariant.category_id == VehicleCategory.id)
            .where(VehicleVariant.id == request.variant_id)
            .where(VehicleVariant.is_active.is_(True))
        )
        row = result.first()
    except SQLAlchemyError:
        logger.exception("Database error while fetching variant %s", request.variant_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reach the database. Please try again shortly.",
        )

    if row is None:
        logger.info("Mileage calculation requested for unknown/inactive variant %s", request.variant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle variant '{request.variant_id}' not found or is inactive",
        )

    variant, category = row

    try:
        fixed_rate = _safe_rate(variant.fixed_per_km, "fixed_per_km", variant.id)
        operating_rate = _safe_rate(variant.operating_per_km, "operating_per_km", variant.id)
        total_rate = float(variant.total_per_km or 0)
        total_rate = _safe_rate(total_rate, "total_per_km", variant.id) if total_rate else (fixed_rate + operating_rate)
    except ValueError as e:
        # Data integrity problem, not the caller's fault -- log loudly for
        # an admin to go fix the offending row, but don't leak internals.
        logger.error("Rate sanity check failed for variant %s: %s", variant.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="This vehicle's rate data failed validation. Please contact support.",
        )

    total_cost = total_rate * request.distance
    fixed_cost = fixed_rate * request.distance
    operating_cost = operating_rate * request.distance

    component_costs = _price_components(variant.components, request.distance)

    response = MileageResponse(
        total_cost=round(total_cost, 2),
        fixed_cost=round(fixed_cost, 2),
        operating_cost=round(operating_cost, 2),
        total_rate=round(total_rate, 4),
        fixed_rate=round(fixed_rate, 4),
        operating_rate=round(operating_rate, 4),
        components=component_costs,
        yearly={
            "year1": float(variant.year1 or 0),
            "year2": float(variant.year2 or 0),
            "year3": float(variant.year3 or 0),
            "year4": float(variant.year4 or 0),
            "year5": float(variant.year5 or 0),
        },
        initial_cost=float(variant.initial_cost or 0),
        method="fastapi",
        distance=request.distance,
    )

    if request.include_forecast:
        response.forecast = _forecast(variant, total_rate, request.distance)

    if request.include_comparison:
        response.comparison = _fuel_type_comparison(variant, category, total_rate)

    logger.info(
        "Priced variant %s (%s) over %.1fkm -> KES %.2f (user=%s)",
        variant.id, variant.label, request.distance, total_cost, user_id or "anonymous",
    )

    # Future: if/when calculation_history exists, persist here when user_id
    # is present:
    #   if user_id:
    #       await db.execute(insert(CalculationHistory).values(
    #           user_id=user_id, variant_id=variant.id, distance=request.distance,
    #           result_json=response.model_dump(by_alias=True),
    #           calculation_version=CALCULATION_VERSION,
    #       ))
    #       await db.commit()

    return response


# =============================================================================
# Helpers
# =============================================================================

def _safe_rate(value: Any, field_name: str, variant_id: UUID) -> float:
    """Guards against corrupt stored rates producing nonsensical costs
    (e.g. a negative rate silently yielding a negative total, or a
    fat-fingered rate 100x too large)."""
    rate = float(value or 0)
    if rate < 0:
        logger.warning("Negative %s (%.4f) on variant %s; clamping to 0", field_name, rate, variant_id)
        return 0.0
    if rate > _MAX_PLAUSIBLE_RATE_PER_KM:
        raise ValueError(f"{field_name}={rate} exceeds plausible maximum ({_MAX_PLAUSIBLE_RATE_PER_KM} KES/km)")
    return rate


def _price_components(components: Optional[dict], distance: float) -> Dict[str, float]:
    """Multiply each stored per-km component rate by distance. Tolerates
    malformed/non-numeric values in the stored JSON rather than failing
    the whole request over one bad field."""
    priced: Dict[str, float] = {}
    for key, per_km_value in (components or {}).items():
        try:
            priced[key] = round(float(per_km_value or 0) * distance, 2)
        except (TypeError, ValueError):
            logger.warning("Non-numeric component '%s'=%r on variant; treating as 0", key, per_km_value)
            priced[key] = 0.0
    return priced


def _forecast(variant: VehicleVariant, total_rate: float, distance: float) -> Dict[str, float]:
    """5-year cost forecast at the requested distance.

    For any year where the variant has an explicit stored yearN figure
    (>0), that authoritative value is used as-is (matches how the
    frontend has always displayed these -- as flat annual figures, not
    scaled by the current trip's distance).

    For years with no stored figure, falls back to a bottom-up estimate:
    each cost COMPONENT is escalated by its own inflation assumption
    (fuel rises faster than insurance, depreciation/interest held flat)
    rather than inflating the total rate uniformly. Still an assumption-
    based MVP forecast, not a measured one -- see _COMPONENT_ANNUAL_INFLATION.
    """
    forecast: Dict[str, float] = {}
    stored_year_values = {
        "year1": float(variant.year1 or 0),
        "year2": float(variant.year2 or 0),
        "year3": float(variant.year3 or 0),
        "year4": float(variant.year4 or 0),
        "year5": float(variant.year5 or 0),
    }
    components = variant.components or {}

    for index, year_key in enumerate(("year1", "year2", "year3", "year4", "year5")):
        stored_value = stored_year_values[year_key]
        if stored_value > 0:
            forecast[year_key] = round(stored_value, 2)
            continue

        years_elapsed = index  # year1 = 0 years elapsed, year5 = 4
        component_total = 0.0
        for comp_key, per_km in components.items():
            try:
                rate = float(per_km or 0)
            except (TypeError, ValueError):
                rate = 0.0
            inflation = _COMPONENT_ANNUAL_INFLATION.get(comp_key, _DEFAULT_COMPONENT_INFLATION)
            component_total += rate * ((1 + inflation) ** years_elapsed) * distance

        # If there were no components at all to build from, fall back
        # further to a flat total-rate estimate so we still return a
        # number rather than zero.
        if not components:
            component_total = total_rate * distance * ((1 + _DEFAULT_COMPONENT_INFLATION) ** years_elapsed)

        forecast[year_key] = round(component_total, 2)

    return forecast


def _fuel_type_comparison(variant: VehicleVariant, category: VehicleCategory, total_rate: float) -> Dict[str, Any]:
    """Compare this variant's rate against the reference average for its fuel type."""
    fuel_type = category.fuel_type or "Unknown"
    average_rate = _get_fuel_type_average_rate(fuel_type)
    return {
        "fuelType": fuel_type,
        "category": category.name,
        "currentRate": round(total_rate, 4),
        "averageRate": average_rate,
        "difference": round(total_rate - average_rate, 4),
        "isBelowAverage": total_rate < average_rate,
    }
