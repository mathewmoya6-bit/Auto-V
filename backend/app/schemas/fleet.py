# app/schemas/fleet.py
# =============================================================================
# AUTO-V API - Fleet Schemas
# =============================================================================
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class FleetCreate(BaseModel):
    name: str
    owner_id: UUID
    description: Optional[str] = None
    vehicle_ids: Optional[List[UUID]] = None


class FleetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    vehicle_ids: Optional[List[UUID]] = None
    is_active: Optional[bool] = None


class FleetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    description: Optional[str] = None
    vehicle_ids: List[UUID] = []
    vehicle_count: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
