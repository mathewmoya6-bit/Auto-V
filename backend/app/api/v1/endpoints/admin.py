# backend/app/api/v1/endpoints/admin.py
# =============================================================================
# Admin Endpoints - CORRECTED
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from app.core.database import get_db
from app.models.user import User  # ← CORRECT: User, not UserProfile
from app.models.vehicle import Vehicle
from app.models.service_request import ServiceRequest
from app.models.payment import Payment
from app.models.certificate import Certificate
from app.api.v1.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# ... rest of the file remains the same ...
