# app/api/v1/routes/instant_value.py
# =============================================================================
# AUTO-V API - Instant Value Check
# =============================================================================
"""
Backs instant-value.html's "Get AI Valuation" flow: the user fills in raw
vehicle specs (no pre-saved vehicle record required) and gets a market
estimate back in one call.

IMPORTANT — same caveat as valuation_service.py: there is no real market-
data source wired up. BASE_PRICE_BY_MAKE below is a rough, hand-entered
reference price per make (approx. KES value of a representative
current-year unit of that make), used purely as the starting point for the
existing depreciation model. Treat these numbers as placeholders — replace
with real comparable-sales data before this is used anywhere with
financial stakes. Keys must match the <option value="..."> strings in
instant-value.html's #make dropdown exactly.

Also NOTE: no M-Pesa integration exists yet. The `phone` field is accepted
and stored on the request but no payment is actually collected — the
service fee shown on the page is currently informational only.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.schemas.user import UserProfile
from app.services.valuation_service import ValuationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/instant-value", tags=["instant-value"])


def get_valuation_service() -> ValuationService:
    return ValuationService()


# ─── Rough reference base prices (KES) — placeholder data, see module docstring ──
BASE_PRICE_BY_MAKE = {
    # Cars
    "Toyota": 3_500_000, "Nissan": 3_000_000, "BMW": 7_500_000,
    "Mercedes": 8_000_000, "Honda": 3_200_000, "Mazda": 3_000_000,
    "Volkswagen": 3_800_000, "Mitsubishi": 3_300_000, "Subaru": 3_600_000,
    "Ford": 3_500_000, "Chevrolet": 3_000_000, "Jeep": 5_500_000,
    "Land Rover": 9_000_000, "Hyundai": 2_800_000, "Kia": 2_700_000,
    "Peugeot": 3_200_000, "Suzuki Car": 2_200_000, "Isuzu": 4_000_000,
    "Daihatsu": 1_800_000,
    # Bikes
    "Honda Bike": 250_000, "Yamaha": 280_000, "Suzuki Bike": 260_000,
    "Kawasaki": 400_000, "TVS": 150_000, "Bajaj": 140_000, "Hero": 130_000,
    "Royal Enfield": 550_000, "KTM": 600_000, "Aprilia": 900_000,
    "BMW Motorrad": 1_800_000, "Ducati": 2_200_000, "Triumph": 1_600_000,
    "Harley Davidson": 2_500_000, "MV Agusta": 2_800_000,
    # Tricycles
    "Piaggio": 450_000, "TVS Tricycle": 400_000, "Bajaj Tricycle": 380_000,
}

# Fallback base price by vehicle type, for makes not in the table above
# (e.g. "Other").
DEFAULT_BASE_PRICE_BY_TYPE = {
    "Car": 2_000_000,
    "Bike": 200_000,
    "Tricycle": 350_000,
}


class InstantValueRequest(BaseModel):
    type: str = Field(..., description="Car | Bike | Tricycle")
    make: str
    model: str
    year: int
    engine_capacity: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    body_color: Optional[str] = None
    mileage: int
    condition: str = "Good"
    accident_history: str = "None"
    location: Optional[str] = None
    previous_owners: Optional[int] = None
    usage_type: Optional[str] = None
    phone: Optional[str] = None


class InstantValueResponse(BaseModel):
    market_value: float
    range_low: float
    range_high: float
    confidence_score: float
    certificate_number: str
    factors: list[str]


def _resolve_condition_key(condition: str, accident_history: str) -> str:
    # A write-off overrides whatever condition the user picked — the
    # depreciation model's multipliers assume "salvage" is the worst case.
    if accident_history == "WriteOff":
        return "salvage"
    if accident_history == "Major":
        return "poor"
    return condition.lower()


@router.post("/calculate", response_model=InstantValueResponse)
async def calculate_instant_value(
    payload: InstantValueRequest,
    current_user: UserProfile = Depends(get_current_user),
    service: ValuationService = Depends(get_valuation_service),
):
    base_price = BASE_PRICE_BY_MAKE.get(
        payload.make,
        DEFAULT_BASE_PRICE_BY_TYPE.get(payload.type, 2_000_000),
    )

    condition_key = _resolve_condition_key(payload.condition, payload.accident_history)

    # Reuses the same depreciation math as the saved-vehicle valuation flow
    # (app/services/valuation_service.py) so both flows stay consistent.
    estimate, confidence, factors = service._estimate(
        base_price=base_price,
        year=payload.year,
        mileage=payload.mileage,
        condition=condition_key,
    )

    certificate_number = f"AUTO-VAL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    logger.info(
        f"Instant valuation for user={current_user.id} "
        f"{payload.make} {payload.model} ({payload.year}) -> KES {estimate:,.0f}"
    )

    return InstantValueResponse(
        market_value=estimate,
        range_low=round(estimate * 0.93, 2),
        range_high=round(estimate * 1.05, 2),
        confidence_score=confidence,
        certificate_number=certificate_number,
        factors=factors,
    )
