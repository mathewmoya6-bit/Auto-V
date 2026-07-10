# backend/app/api/v1/endpoints/profile.py
# =============================================================================
# Profile Endpoints - CORRECTED
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import logging

from app.core.database import get_db
from app.models.user import User  # ← CORRECT: User, not UserProfile
from app.api.v1.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# ... rest of the file remains the same ...
