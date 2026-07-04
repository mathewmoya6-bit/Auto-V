# app/models/payment.py
# =============================================================================
# AUTO-V API - Payment Model
# =============================================================================

import uuid
from sqlalchemy import Column, String, DateTime, Numeric, JSON, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)

    service_type = Column(String(50), nullable=False)  # valuation, inspection, mileage, fleet, certificate...
    purpose = Column(String(100))
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(20), default="mpesa")  # mpesa, card, bank, cash
    status = Column(String(20), default="pending")  # pending, processing, completed, failed, refunded, cancelled
    reference = Column(String(50), unique=True)

    mpesa_phone = Column(String(50))
    transaction_id = Column(String(100))
    checkout_request_id = Column(String(100))
    mpesa_receipt = Column(String(100))
    payment_data = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship(
        "UserProfile", 
        foreign_keys=[user_id],  # ← ADDED: Explicit foreign_keys
        back_populates="payments"
    )

    __table_args__ = (
        Index("idx_payments_user_id", "user_id"),
        Index("idx_payments_status", "status"),
        UniqueConstraint("reference", name="uq_payments_reference"),
        {"schema": "public"},  # ← ADDED: Explicit schema
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "service_type": self.service_type,
            "amount": float(self.amount) if self.amount else 0,
            "payment_method": self.payment_method,
            "status": self.status,
            "reference": self.reference,
            "mpesa_receipt": self.mpesa_receipt,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
