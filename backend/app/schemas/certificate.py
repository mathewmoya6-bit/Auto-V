# app/schemas/certificate.py
# =============================================================================
# AUTO-V API - Certificate Schemas
# =============================================================================
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CertificateCreate(BaseModel):
    vehicle_id: UUID
    valuation_id: Optional[UUID] = None
    certificate_type: str = "valuation"
    issued_to: Optional[str] = None


class CertificateUpdate(BaseModel):
    certificate_type: Optional[str] = None
    issued_to: Optional[str] = None
    is_valid: Optional[bool] = None


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    valuation_id: Optional[UUID] = None
    certificate_number: str
    certificate_type: str
    issued_to: Optional[str] = None
    pdf_url: Optional[str] = None
    is_valid: bool = True
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
