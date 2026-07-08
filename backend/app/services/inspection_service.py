# app/services/inspection_service.py
# =============================================================================
# AUTO-V API - Inspection Service
# =============================================================================
import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import HTTPException, status

from app.core.database import get_admin_client
from app.schemas.inspection import (
    InspectionComplete,
    InspectionCreate,
    InspectionItem,
    InspectionItemStatus,
    InspectionResponse,
    InspectionStatus,
    InspectionUpdate,
    ItemSeverity,
)
from app.services.vehicle_service import VehicleService

logger = logging.getLogger(__name__)

TABLE_NAME = "inspections"

# Deduction per failed/warning item, scaled by severity. Documented
# assumption, not a regulatory standard — adjust to match your actual
# inspection checklist weighting once you have one.
_SEVERITY_DEDUCTION = {
    ItemSeverity.MINOR: 3,
    ItemSeverity.MODERATE: 8,
    ItemSeverity.MAJOR: 18,
    ItemSeverity.SAFETY_CRITICAL: 35,
}
_DEFAULT_DEDUCTION = 8  # used when an item fails/warns but has no severity set


class InspectionService:
    def __init__(self):
        self.db = get_admin_client()
        self.vehicles = VehicleService()

    async def create_inspection(self, user_id: UUID, payload: InspectionCreate) -> InspectionResponse:
        # Confirms the vehicle exists and belongs to this user before scheduling
        await self.vehicles.get_vehicle(payload.vehicle_id, user_id)

        record = payload.model_dump(mode="json")
        record["user_id"] = str(user_id)
        record["status"] = InspectionStatus.SCHEDULED.value
        record["items"] = []
        record["created_at"] = datetime.now(timezone.utc).isoformat()

        result = self.db.table(TABLE_NAME).insert(record).execute()
        if not result.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create inspection")
        return InspectionResponse(**result.data[0])

    async def list_inspections(self, user_id: UUID) -> List[InspectionResponse]:
        result = (
            self.db.table(TABLE_NAME)
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        return [InspectionResponse(**row) for row in result.data]

    async def get_inspection(self, inspection_id: UUID, user_id: UUID, is_admin: bool = False) -> InspectionResponse:
        result = self.db.table(TABLE_NAME).select("*").eq("id", str(inspection_id)).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
        inspection = result.data[0]
        if not is_admin and str(inspection["user_id"]) != str(user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your inspection")
        return InspectionResponse(**inspection)

    async def update_inspection(
        self, inspection_id: UUID, user_id: UUID, payload: InspectionUpdate, is_admin: bool = False
    ) -> InspectionResponse:
        await self.get_inspection(inspection_id, user_id, is_admin)
        updates = {k: v for k, v in payload.model_dump(mode="json").items() if v is not None}

        result = self.db.table(TABLE_NAME).update(updates).eq("id", str(inspection_id)).execute()
        if not result.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update inspection")
        return InspectionResponse(**result.data[0])

    async def complete_inspection(
        self, inspection_id: UUID, inspector_id: UUID, payload: InspectionComplete
    ) -> InspectionResponse:
        """Inspector/admin-only: submits final checklist items, computes a
        score from them, and marks the inspection completed."""
        existing = self.db.table(TABLE_NAME).select("*").eq("id", str(inspection_id)).limit(1).execute()
        if not existing.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

        score, condition = self._score_items(payload.items)

        updates = {
            "items": [item.model_dump(mode="json") for item in payload.items],
            "inspector_notes": payload.inspector_notes,
            "inspector_id": str(inspector_id),
            "overall_score": score,
            "overall_condition": condition,
            "status": InspectionStatus.COMPLETED.value,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        result = self.db.table(TABLE_NAME).update(updates).eq("id", str(inspection_id)).execute()
        if not result.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete inspection")
        return InspectionResponse(**result.data[0])

    async def delete_inspection(self, inspection_id: UUID, user_id: UUID, is_admin: bool = False) -> None:
        await self.get_inspection(inspection_id, user_id, is_admin)
        self.db.table(TABLE_NAME).delete().eq("id", str(inspection_id)).execute()

    @staticmethod
    def _score_items(items: List[InspectionItem]):
        """Starts at 100, deducts per failed/warning item by severity.
        Documented assumption-based scoring — replace _SEVERITY_DEDUCTION
        with your actual checklist weighting when you have one."""
        scored_items = [i for i in items if i.status != InspectionItemStatus.NOT_APPLICABLE]
        if not scored_items:
            return None, None

        score = 100.0
        for item in scored_items:
            if item.status in (InspectionItemStatus.FAIL, InspectionItemStatus.WARNING):
                deduction = _SEVERITY_DEDUCTION.get(item.severity, _DEFAULT_DEDUCTION)
                score -= deduction

        score = max(score, 0.0)

        if score >= 90:
            condition = "excellent"
        elif score >= 75:
            condition = "good"
        elif score >= 55:
            condition = "fair"
        else:
            condition = "poor"

        return round(score, 1), condition
