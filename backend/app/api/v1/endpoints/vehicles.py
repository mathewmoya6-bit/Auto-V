# backend/app/api/v1/endpoints/vehicles.py
# =============================================================================
# Vehicle Endpoints - CORRECTED
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional, List
import uuid
import logging

from app.core.database import get_db
from app.models.vehicle import Vehicle
from app.models.user import User  # ← CORRECT: User, not UserProfile
from app.api.v1.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# ... rest of the file remains the same ...

@router.post("/vehicles")
async def create_vehicle(
    request: VehicleCreate,
    current_user: User = Depends(get_current_user),  # ← CORRECT: User
    db: AsyncSession = Depends(get_db)
):
    # ... uses User model ...
    pass
