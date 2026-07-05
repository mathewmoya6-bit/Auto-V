# backend/app/api/v1/endpoints/auth.py
# =============================================================================
# Authentication Endpoints - CORRECTED
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import bcrypt
import jwt
from datetime import datetime, timedelta
import uuid
import logging

from app.core.database import get_db
from app.models.user import User  # ← CORRECT: User, not UserProfile
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ... rest of the file remains the same ...

@router.post("/auth/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # ... uses User model ...
    pass

@router.post("/auth/login")
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    # ... uses User model ...
    pass

@router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    # ... uses User model ...
    pass

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    # ... uses User model ...
    pass
