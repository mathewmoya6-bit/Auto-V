# app/api/v1/routes/certificates.py
# =============================================================================
# AUTO-V API - Certificate / Verification Routes
# =============================================================================

import logging
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.certificate import Certificate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get("/verify/{certificate_number}")
async def verify_certificate(certificate_number: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint: verify a certificate by its number (used by QR code scans)."""
    result = await db.execute(select(Certificate).where(Certificate.certificate_number == certificate_number))
    cert = result.scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    if cert.status != "active":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=f"Certificate is {cert.status}")
    return cert.to_dict()


@router.get("/{certificate_id}")
async def get_certificate(certificate_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Certificate).where(Certificate.id == certificate_id))
    cert = result.scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    return cert.to_dict()
