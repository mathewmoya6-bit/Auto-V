# backend/app/api/v1/endpoints/valuations.py
# =============================================================================
# Valuation Endpoints
#
# STATUS: import-safe stub, NOT a real implementation.
#
# This file previously referenced `ValuationRequest` without defining or
# importing it (NameError on startup), and every endpoint body was just
# `pass` (would have returned null to callers even if it had imported).
#
# I don't have visibility into what a real valuation request/response should
# contain, what `Valuation` model fields actually look like, or what the
# scoring/AI logic is meant to do -- so rather than invent fake business
# logic, this version:
#   1. Defines ValuationRequest with a reasonable guess at fields (EDIT THESE
#      to match whatever your valuation form / AI pipeline actually needs).
#   2. Makes the file import cleanly, unblocking the rest of api.py.
#   3. Returns 501 Not Implemented from both endpoints instead of silently
#      returning None, so callers get an honest error instead of broken data.
#
# Replace the bodies of create_valuation / get_valuations with real logic
# (OpenAI / Google Vision calls, scoring, persistence) when ready.
# =============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging

from app.core.database import get_db
from app.models.valuation import Valuation
from app.models.vehicle import Vehicle
from app.models.user import UserProfile as User
from app.api.v1.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# -----------------------------------------------------------------------------
# TODO: confirm these fields match what the valuation form / pipeline needs.
# This is a placeholder guess based on the models imported above (Vehicle-
# linked valuation), not a spec you gave me.
# -----------------------------------------------------------------------------
class ValuationRequest(BaseModel):
    vehicle_id: uuid.UUID
    notes: Optional[str] = None
    requested_at: Optional[datetime] = None


@router.post("/valuations", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_valuation(
    request: ValuationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.warning(
        "POST /valuations called but valuation logic is not yet implemented "
        "(vehicle_id=%s, user=%s)",
        request.vehicle_id,
        current_user.id,
    )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Valuation creation is not implemented yet.",
    )


@router.get("/valuations", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_valuations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.warning(
        "GET /valuations called but valuation logic is not yet implemented (user=%s)",
        current_user.id,
    )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Fetching valuations is not implemented yet.",
    )
