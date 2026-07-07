# app/schemas/payment.py
# =============================================================================
# AUTO-V API - Payment Schemas
# =============================================================================
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    user_id: UUID
    amount: float
    currency: str = "KES"
    description: Optional[str] = None
    related_entity_id: Optional[UUID] = None  # e.g. valuation_id, certificate_id


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    amount: float
    currency: str = "KES"
    status: str
    description: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── M-Pesa specific schemas, matching app/services/mpesa.py's stk_push() ──

class MpesaPaymentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    phone_number: str = Field(..., description="Format: 2547XXXXXXXX")
    account_reference: str
    transaction_desc: str


class MpesaPaymentResponse(BaseModel):
    success: bool
    message: str
    checkout_request_id: Optional[str] = None
    merchant_request_id: Optional[str] = None
