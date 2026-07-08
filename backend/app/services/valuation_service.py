# app/services/valuation_service.py
# =============================================================================
# AUTO-V API - Valuation Service
# =============================================================================
"""
IMPORTANT — read before trusting these numbers in production:

There is no market-comparables data source wired up yet (no third-party
API, no internal sales-history table). The formula below is a standard,
transparent declining-balance depreciation model parameterized with
commonly-cited rule-of-thumb rates for the Kenyan used-car market. It is
a reasonable MVP estimate, not a calibrated one — replace
_depreciate_by_age(), _mileage_adjustment(), and CONDITION_MULTIPLIER
with real data (comparable sales, a licensed valuation API, or a trained
model) before this number is used for anything with financial stakes
(loans, insurance, resale pricing).
"""
import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import HTTPException, status

from app.core.database import get_admin_client
from app.schemas.valuation import ValuationRequest, ValuationResponse
from app.services.vehicle_service import VehicleService

logger = logging.getLogger(__name__)

TABLE_NAME = "valuations"

# ─── Depreciation assumptions (document your real source when you have one) ──
FIRST_YEAR_DEPRECIATION = 0.20   # value lost in year 1
ANNUAL_DEPRECIATION = 0.12       # value lost each subsequent year
MIN_RESIDUAL_FRACTION = 0.10     # floor: never value below 10% of base_price

EXPECTED_KM_PER_YEAR = 15_000
EXCESS_MILEAGE_PENALTY_PER_KM = 2.0  # KES deducted per km over expected mileage

CONDITION_MULTIPLIER = {
    "excellent": 1.08,
    "good": 1.00,
    "fair": 0.85,
    "poor": 0.65,
    "salvage": 0.40,
}

RANGE_SPREAD = 0.07  # +/- 7% around the point estimate


class ValuationService:
    def __init__(self):
        self.db = get_admin_client()
        self.vehicles = VehicleService()

    async def create_valuation(self, user_id: UUID, payload: ValuationRequest) -> ValuationResponse:
        vehicle = await self.vehicles.get_vehicle(payload.vehicle_id, user_id)

        estimate, confidence, factors = self._estimate(
            base_price=payload.base_price,
            year=vehicle.year,
            mileage=vehicle.mileage,
            condition=payload.condition_override or vehicle.condition or "good",
        )

        record = {
            "vehicle_id": str(payload.vehicle_id),
            "user_id": str(user_id),
            "estimated_value": estimate,
            "estimated_value_range_low": round(estimate * (1 - RANGE_SPREAD), 2),
            "estimated_value_range_high": round(estimate * (1 + RANGE_SPREAD), 2),
            "confidence_score": confidence,
            "method": "depreciation_model_v1",
            "factors": factors,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = self.db.table(TABLE_NAME).insert(record).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save valuation",
            )
        return ValuationResponse(**result.data[0])

    async def instant_value(self, user_id: UUID, payload: ValuationRequest) -> ValuationResponse:
        """Same computation as create_valuation but not persisted — for quick previews."""
        vehicle = await self.vehicles.get_vehicle(payload.vehicle_id, user_id)

        estimate, confidence, factors = self._estimate(
            base_price=payload.base_price,
            year=vehicle.year,
            mileage=vehicle.mileage,
            condition=payload.condition_override or vehicle.condition or "good",
        )

        return ValuationResponse(
            vehicle_id=payload.vehicle_id,
            user_id=user_id,
            estimated_value=estimate,
            estimated_value_range_low=round(estimate * (1 - RANGE_SPREAD), 2),
            estimated_value_range_high=round(estimate * (1 + RANGE_SPREAD), 2),
            confidence_score=confidence,
            method="depreciation_model_v1_instant",
            factors=factors,
        )

    def _estimate(self, base_price: float, year: int, mileage, condition: str):
        factors: List[str] = []
        current_year = datetime.now().year
        age = max(current_year - year, 0)

        value = base_price
        if age >= 1:
            value *= (1 - FIRST_YEAR_DEPRECIATION)
            factors.append(f"first_year_depreciation:-{FIRST_YEAR_DEPRECIATION*100:.0f}%")
            if age > 1:
                value *= (1 - ANNUAL_DEPRECIATION) ** (age - 1)
                factors.append(f"annual_depreciation:-{ANNUAL_DEPRECIATION*100:.0f}%/yr x{age-1}yrs")

        floor = base_price * MIN_RESIDUAL_FRACTION
        value = max(value, floor)

        if mileage is not None:
            expected_mileage = age * EXPECTED_KM_PER_YEAR
            excess = max(mileage - expected_mileage, 0)
            penalty = excess * EXCESS_MILEAGE_PENALTY_PER_KM
            if penalty > 0:
                value = max(value - penalty, floor)
                factors.append(f"excess_mileage_penalty:-KES{penalty:,.0f} ({excess:,.0f}km over expected)")

        multiplier = CONDITION_MULTIPLIER.get(condition, 1.0)
        value *= multiplier
        factors.append(f"condition:{condition} x{multiplier}")

        confidence = 55.0
        if mileage is not None:
            confidence += 15
        if condition:
            confidence += 15
        confidence = min(confidence, 85.0)  # capped — this is an unvalidated formula, not measured accuracy

        return round(value, 2), confidence, factors
