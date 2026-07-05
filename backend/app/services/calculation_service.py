# backend/app/services/calculation_service.py
# ============================================================
# Mileage Calculation Service
# ============================================================

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any
import logging

from app.models.vehicle_variant import VehicleVariant

logger = logging.getLogger(__name__)

class CalculationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_mileage(
        self,
        variant_id: str,
        distance: float,
        include_forecast: bool = False,
        include_comparison: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate mileage costs with business logic.
        """
        try:
            # 1. Fetch variant from database
            query = select(VehicleVariant).where(VehicleVariant.id == variant_id)
            result = await self.db.execute(query)
            variant = result.scalar_one_or_none()

            if not variant:
                raise ValueError(f"Variant {variant_id} not found")

            # 2. Calculate costs
            fixed_rate = float(variant.fixed_per_km or 0)
            operating_rate = float(variant.operating_per_km or 0)
            total_rate = float(variant.total_per_km or (fixed_rate + operating_rate))

            # 3. Calculate trip costs
            total_cost = total_rate * distance
            fixed_cost = fixed_rate * distance
            operating_cost = operating_rate * distance

            # 4. Calculate component costs
            components = variant.components or {}
            component_costs = {}
            for key, value in components.items():
                component_costs[key] = float(value or 0) * distance

            # 5. Return comprehensive result
            return {
                "totalCost": total_cost,
                "fixedCost": fixed_cost,
                "operatingCost": operating_cost,
                "totalRate": total_rate,
                "fixedRate": fixed_rate,
                "operatingRate": operating_rate,
                "components": component_costs,
                "yearly": {
                    "year1": float(variant.year1 or 0),
                    "year2": float(variant.year2 or 0),
                    "year3": float(variant.year3 or 0),
                    "year4": float(variant.year4 or 0),
                    "year5": float(variant.year5 or 0)
                },
                "initialCost": float(variant.initial_cost or 0),
                "method": "fastapi"
            }

        except Exception as e:
            logger.error(f"Calculation error: {e}")
            raise
