# app/services/vehicle_service.py
# =============================================================================
# AUTO-V API - Vehicle Service
# =============================================================================
import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import HTTPException, status

from app.core.database import get_admin_client
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate

logger = logging.getLogger(__name__)

TABLE_NAME = "vehicles"


class VehicleService:
    def __init__(self):
        self.db = get_admin_client()

    async def create_vehicle(self, owner_id: UUID, payload: VehicleCreate) -> VehicleResponse:
        record = payload.model_dump()
        record["owner_id"] = str(owner_id)
        record["created_at"] = datetime.now(timezone.utc).isoformat()

        result = self.db.table(TABLE_NAME).insert(record).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create vehicle",
            )
        return VehicleResponse(**result.data[0])

    async def list_vehicles(self, owner_id: UUID) -> List[VehicleResponse]:
        result = (
            self.db.table(TABLE_NAME)
            .select("*")
            .eq("owner_id", str(owner_id))
            .order("created_at", desc=True)
            .execute()
        )
        return [VehicleResponse(**row) for row in result.data]

    async def get_vehicle(self, vehicle_id: UUID, owner_id: UUID, is_admin: bool = False) -> VehicleResponse:
        query = self.db.table(TABLE_NAME).select("*").eq("id", str(vehicle_id))
        result = query.limit(1).execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        vehicle = result.data[0]
        if not is_admin and str(vehicle["owner_id"]) != str(owner_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your vehicle")

        return VehicleResponse(**vehicle)

    async def update_vehicle(
        self, vehicle_id: UUID, owner_id: UUID, payload: VehicleUpdate, is_admin: bool = False
    ) -> VehicleResponse:
        # Raises 404/403 as appropriate before allowing the update
        await self.get_vehicle(vehicle_id, owner_id, is_admin)

        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = (
            self.db.table(TABLE_NAME).update(updates).eq("id", str(vehicle_id)).execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update vehicle",
            )
        return VehicleResponse(**result.data[0])

    async def delete_vehicle(self, vehicle_id: UUID, owner_id: UUID, is_admin: bool = False) -> None:
        await self.get_vehicle(vehicle_id, owner_id, is_admin)
        self.db.table(TABLE_NAME).delete().eq("id", str(vehicle_id)).execute()
