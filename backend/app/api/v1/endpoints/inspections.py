# backend/app/api/v1/endpoints/inspections.py
# =============================================================================
# Inspection Endpoints - CORRECTED
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging

from app.core.database import get_db
from app.models.inspection import Inspection
from app.models.vehicle import Vehicle
from app.models.user import User  # ← CORRECT: User, not UserProfile
from app.api.v1.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# ... rest of the file remains the same ...

@router.post("/inspections")
async def create_inspection(
    request: InspectionRequest,
    current_user: User = Depends(get_current_user),  # ← CORRECT: User
    db: AsyncSession = Depends(get_db)
):
    # ... uses User model ...
    pass

@router.get("/inspections")
async def get_inspections(
    current_user: User = Depends(get_current_user),  # ← CORRECT: User
    db: AsyncSession = Depends(get_db)
):
    # ... uses User model ...
    pass
