# app/services/mileage_service.py
# =============================================================================
# AUTO-V API - Mileage Service
# =============================================================================
"""
The pricing engine below (_safe_rate, _price_components, _forecast,
_fuel_type_comparison, calculate_trip_cost) is ported from the original
SQLAlchemy-based app/api/v1/endpoints/calculate.py — same formulas, same
sanity checks, same 5-year forecast logic. Only the data-access layer
changed (Supabase client instead of AsyncSession). See that file's
history if you need to diff the math.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.core.database import get_admin_client, get_supabase
from app.schemas.mileage import (
    MileageApprovalRequest,
    MileageCalculateRequest,
    MileageCalculateResponse,
    MileageClaimCreate,
    MileageClaimResponse,
    MileageClaimSummary,
    MileageClaimUpdate,
    RouteResponse,
    VehicleCategoryResponse,
    VehicleVariantResponse,
)

logger = logging.getLogger(__name__)

CATEGORIES_TABLE = "vehicle_categories"
VARIANTS_TABLE = "vehicle_variants"
ROUTES_TABLE = "routes"
CLAIMS_TABLE = "mileage_claims"

CALCULATION_VERSION = "2.0"

_FUEL_TYPE_AVERAGE_RATE = {
    "Petrol": 45.00,
    "Diesel": 52.00,
    "Electric": 30.00,
    "LPG": 38.00,
}
_DEFAULT_AVERAGE_RATE = 45.00

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

_MAX_PLAUSIBLE_RATE_PER_KM = 10_000.0


class MileageService:
    def __init__(self):
        self.db = get_supabase()      # reads — RLS-respecting
        self.admin = get_admin_client()  # writes — bypasses RLS

    # ─── Reference data ────────────────────────────────────────────

    async def list_categories(self) -> List[VehicleCategoryResponse]:
        result = self.db.table(CATEGORIES_TABLE).select("*").eq("is_active", True).execute()
        return [VehicleCategoryResponse(**row) for row in result.data]

    async def list_variants(self, category_id: Optional[UUID] = None) -> List[VehicleVariantResponse]:
        query = self.db.table(VARIANTS_TABLE).select("*").eq("is_active", True)
        if category_id is not None:
            query = query.eq("category_id", str(category_id))
        result = query.order("label").execute()
        return [VehicleVariantResponse(**row) for row in result.data]

    async def get_variant(self, variant_id: UUID) -> VehicleVariantResponse:
        result = (
            self.db.table(VARIANTS_TABLE)
            .select("*")
            .eq("id", str(variant_id))
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle variant not found")
        return VehicleVariantResponse(**result.data[0])

    async def list_routes(self) -> List[RouteResponse]:
        result = self.db.table(ROUTES_TABLE).select("*").eq("is_active", True).execute()
        return [RouteResponse(**row) for row in result.data]

    # ─── Trip cost calculation (ported pricing engine) ─────────────

    async def calculate_trip_cost(
        self, request: MileageCalculateRequest, user_id: Optional[str] = None
    ) -> MileageCalculateResponse:
        variant_result = (
            self.db.table(VARIANTS_TABLE)
            .select("*")
            .eq("id", str(request.variant_id))
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not variant_result.data:
            logger.info("Mileage calculation requested for unknown/inactive variant %s", request.variant_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle variant '{request.variant_id}' not found or is inactive",
            )
        variant = variant_result.data[0]

        category = None
        if request.include_comparison:
            cat_result = (
                self.db.table(CATEGORIES_TABLE)
                .select("*")
                .eq("id", variant["category_id"])
                .limit(1)
                .execute()
            )
            category = cat_result.data[0] if cat_result.data else None

        try:
            fixed_rate = self._safe_rate(variant.get("fixed_per_km"), "fixed_per_km", variant["id"])
            operating_rate = self._safe_rate(variant.get("operating_per_km"), "operating_per_km", variant["id"])
            stored_total = float(variant.get("total_per_km") or 0)
            total_rate = (
                self._safe_rate(stored_total, "total_per_km", variant["id"])
                if stored_total
                else (fixed_rate + operating_rate)
            )
        except ValueError as e:
            logger.error("Rate sanity check failed for variant %s: %s", variant["id"], e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="This vehicle's rate data failed validation. Please contact support.",
            )

        total_cost = total_rate * request.distance
        fixed_cost = fixed_rate * request.distance
        operating_cost = operating_rate * request.distance

        component_costs = self._price_components(variant.get("components"), request.distance)

        response = MileageCalculateResponse(
            total_cost=round(total_cost, 2),
            fixed_cost=round(fixed_cost, 2),
            operating_cost=round(operating_cost, 2),
            total_rate=round(total_rate, 4),
            fixed_rate=round(fixed_rate, 4),
            operating_rate=round(operating_rate, 4),
            components=component_costs,
            yearly={
                "year1": float(variant.get("year1") or 0),
                "year2": float(variant.get("year2") or 0),
                "year3": float(variant.get("year3") or 0),
                "year4": float(variant.get("year4") or 0),
                "year5": float(variant.get("year5") or 0),
            },
            initial_cost=float(variant.get("initial_cost") or 0),
            distance=request.distance,
        )

        if request.include_forecast:
            response.forecast = self._forecast(variant, total_rate, request.distance)

        if request.include_comparison and category is not None:
            response.comparison = self._fuel_type_comparison(variant, category, total_rate)

        logger.info(
            "Priced variant %s (%s) over %.1fkm -> KES %.2f (user=%s)",
            variant["id"], variant.get("label"), request.distance, total_cost, user_id or "anonymous",
        )

        return response

    @staticmethod
    def _safe_rate(value: Any, field_name: str, variant_id) -> float:
        rate = float(value or 0)
        if rate < 0:
            logger.warning("Negative %s (%.4f) on variant %s; clamping to 0", field_name, rate, variant_id)
            return 0.0
        if rate > _MAX_PLAUSIBLE_RATE_PER_KM:
            raise ValueError(f"{field_name}={rate} exceeds plausible maximum ({_MAX_PLAUSIBLE_RATE_PER_KM} KES/km)")
        return rate

    @staticmethod
    def _price_components(components: Optional[dict], distance: float) -> Dict[str, float]:
        priced: Dict[str, float] = {}
        for key, per_km_value in (components or {}).items():
            try:
                priced[key] = round(float(per_km_value or 0) * distance, 2)
            except (TypeError, ValueError):
                logger.warning("Non-numeric component '%s'=%r on variant; treating as 0", key, per_km_value)
                priced[key] = 0.0
        return priced

    @staticmethod
    def _forecast(variant: dict, total_rate: float, distance: float) -> Dict[str, float]:
        forecast: Dict[str, float] = {}
        stored_year_values = {
            "year1": float(variant.get("year1") or 0),
            "year2": float(variant.get("year2") or 0),
            "year3": float(variant.get("year3") or 0),
            "year4": float(variant.get("year4") or 0),
            "year5": float(variant.get("year5") or 0),
        }
        components = variant.get("components") or {}

        for index, year_key in enumerate(("year1", "year2", "year3", "year4", "year5")):
            stored_value = stored_year_values[year_key]
            if stored_value > 0:
                forecast[year_key] = round(stored_value, 2)
                continue

            years_elapsed = index
            component_total = 0.0
            for comp_key, per_km in components.items():
                try:
                    rate = float(per_km or 0)
                except (TypeError, ValueError):
                    rate = 0.0
                inflation = _COMPONENT_ANNUAL_INFLATION.get(comp_key, _DEFAULT_COMPONENT_INFLATION)
                component_total += rate * ((1 + inflation) ** years_elapsed) * distance

            if not components:
                component_total = total_rate * distance * ((1 + _DEFAULT_COMPONENT_INFLATION) ** years_elapsed)

            forecast[year_key] = round(component_total, 2)

        return forecast

    @staticmethod
    def _fuel_type_comparison(variant: dict, category: dict, total_rate: float) -> Dict[str, Any]:
        fuel_type = category.get("fuel_type") or "Unknown"
        average_rate = _FUEL_TYPE_AVERAGE_RATE.get(fuel_type, _DEFAULT_AVERAGE_RATE)
        return {
            "fuelType": fuel_type,
            "category": category.get("name"),
            "currentRate": round(total_rate, 4),
            "averageRate": average_rate,
            "difference": round(total_rate - average_rate, 4),
            "isBelowAverage": total_rate < average_rate,
        }

    # ─── Claims CRUD ────────────────────────────────────────────────

    async def create_claim(self, user_id: UUID, payload: MileageClaimCreate) -> MileageClaimResponse:
        record = payload.model_dump(mode="json")
        record["user_id"] = str(user_id)
        record["claim_amount"] = round(payload.distance_km * payload.rate_per_km, 2)
        record["status"] = "pending"
        record["created_at"] = datetime.now(timezone.utc).isoformat()

        result = self.admin.table(CLAIMS_TABLE).insert(record).execute()
        if not result.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create claim")
        return MileageClaimResponse(**result.data[0])

    async def list_claims(self, user_id: UUID) -> List[MileageClaimResponse]:
        result = (
            self.admin.table(CLAIMS_TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        return [MileageClaimResponse(**row) for row in result.data]

    async def get_claim(self, claim_id: UUID, user_id: UUID, is_admin: bool = False) -> MileageClaimResponse:
        result = self.admin.table(CLAIMS_TABLE).select("*").eq("id", str(claim_id)).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
        claim = result.data[0]
        if not is_admin and str(claim["user_id"]) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your claim")
        return MileageClaimResponse(**claim)

    async def update_claim(
        self, claim_id: UUID, user_id: UUID, payload: MileageClaimUpdate, is_admin: bool = False
    ) -> MileageClaimResponse:
        await self.get_claim(claim_id, user_id, is_admin)
        updates = {k: v for k, v in payload.model_dump(mode="json").items() if v is not None}
        if "distance_km" in updates or "rate_per_km" in updates:
            existing = self.admin.table(CLAIMS_TABLE).select("*").eq("id", str(claim_id)).limit(1).execute().data[0]
            distance = updates.get("distance_km", existing["distance_km"])
            rate = updates.get("rate_per_km", existing["rate_per_km"])
            updates["claim_amount"] = round(distance * rate, 2)

        result = self.admin.table(CLAIMS_TABLE).update(updates).eq("id", str(claim_id)).execute()
        if not result.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update claim")
        return MileageClaimResponse(**result.data[0])

    async def approve_claim(self, claim_id: UUID, admin_id: UUID, payload: MileageApprovalRequest) -> MileageClaimResponse:
        updates = {
            "status": "approved" if payload.approve else "rejected",
            "approved_by": str(admin_id),
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }
        result = self.admin.table(CLAIMS_TABLE).update(updates).eq("id", str(claim_id)).execute()
        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
        return MileageClaimResponse(**result.data[0])

    async def claims_summary(self, user_id: UUID) -> MileageClaimSummary:
        result = self.admin.table(CLAIMS_TABLE).select("*").eq("user_id", str(user_id)).execute()
        claims = result.data or []

        return MileageClaimSummary(
            total_claims=len(claims),
            total_distance_km=sum(float(c.get("distance_km") or 0) for c in claims),
            total_claim_amount=sum(float(c.get("claim_amount") or 0) for c in claims),
            pending_claims=sum(1 for c in claims if c.get("status") == "pending"),
            approved_claims=sum(1 for c in claims if c.get("status") == "approved"),
            rejected_claims=sum(1 for c in claims if c.get("status") == "rejected"),
        )
