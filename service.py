# app/services/instant_value_service.py
"""
Business logic for Instant Value estimates.

TODO(integration): Replace the heuristic in `_estimate_base_value` with
whatever pricing/market-data source your real Valuation module already uses
(e.g. app/services/valuation_service.py). This is written as a pure function
so it's easy to swap out without touching the router.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.schemas.instant_value import (
    InstantValueRequest,
    InstantValueResponse,
    ValueFactor,
    VehicleCondition,
)

CONDITION_MULTIPLIER = {
    VehicleCondition.excellent: 1.10,
    VehicleCondition.good: 1.00,
    VehicleCondition.fair: 0.85,
    VehicleCondition.poor: 0.65,
}

# TODO(integration): swap for a real base-price lookup (make/model/year table,
# external pricing API, or your existing valuation dataset).
_FALLBACK_BASE_PRICE = 15000.0


def _estimate_base_value(make: str, model: str, year: int) -> float:
    current_year = datetime.now(timezone.utc).year
    age = max(current_year - year, 0)
    # simple straight-line depreciation floor at 20% of base price
    depreciation = min(age * 0.06, 0.80)
    return _FALLBACK_BASE_PRICE * (1 - depreciation)


def _mileage_adjustment(mileage: int, year: int) -> float:
    current_year = datetime.now(timezone.utc).year
    age_years = max(current_year - year, 1)
    expected_mileage = age_years * 15000  # rough average km/year
    delta = mileage - expected_mileage
    # every 10,000km over/under expected shifts value ~2%
    return -0.02 * (delta / 10000)


def calculate_instant_value(payload: InstantValueRequest) -> InstantValueResponse:
    base_value = _estimate_base_value(payload.make, payload.model, payload.year)
    condition_mult = CONDITION_MULTIPLIER[payload.condition]
    mileage_adj = _mileage_adjustment(payload.mileage, payload.year)

    estimated_value = base_value * condition_mult * (1 + mileage_adj)
    estimated_value = max(estimated_value, 0)

    factors = [
        ValueFactor(
            label="Age & base depreciation",
            impact_percent=round((base_value / _FALLBACK_BASE_PRICE - 1) * 100, 1),
            description=f"{payload.year} model year depreciation applied.",
        ),
        ValueFactor(
            label="Condition",
            impact_percent=round((condition_mult - 1) * 100, 1),
            description=f"Reported condition: {payload.condition.value}.",
        ),
        ValueFactor(
            label="Mileage vs. expected",
            impact_percent=round(mileage_adj * 100, 1),
            description=f"{payload.mileage:,} km on the odometer.",
        ),
    ]

    return InstantValueResponse(
        id=None,
        make=payload.make,
        model=payload.model,
        year=payload.year,
        mileage=payload.mileage,
        condition=payload.condition,
        estimated_value=round(estimated_value, 2),
        value_range_low=round(estimated_value * 0.92, 2),
        value_range_high=round(estimated_value * 1.08, 2),
        confidence_score=0.75,  # TODO(integration): derive from data completeness
        factors=factors,
        generated_at=datetime.now(timezone.utc),
        saved=False,
    )


# --- Persistence helpers -----------------------------------------------------
# TODO(integration): back these with a real InstantValueEstimate SQLAlchemy
# model + your DB session. Left as an interface so the router works standalone.

async def save_estimate(db, user_id: UUID, payload: InstantValueRequest, result: InstantValueResponse):
    """Persist an estimate for a logged-in user's history. Stub — wire to your DB."""
    result.id = uuid4()
    result.saved = True
    # e.g.:
    # row = InstantValueEstimate(id=result.id, user_id=user_id, **payload.model_dump(), **result.model_dump())
    # db.add(row); await db.commit()
    return result


async def get_estimate_by_id(db, user_id: UUID, estimate_id: UUID) -> Optional[InstantValueResponse]:
    """Stub — replace with real lookup, scoped to the owning user."""
    return None


async def list_user_estimates(db, user_id: UUID) -> list:
    """Stub — replace with real query."""
    return []
