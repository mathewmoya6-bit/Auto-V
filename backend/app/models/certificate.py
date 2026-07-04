# app/models/certificate.py
# =============================================================================
# AUTO-V API - Certificate Model (verification / QR reports)
# =============================================================================

import uuid
from sqlalchemy import Column, String, DateTime, Date, JSON, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)

    certificate_number = Column(String(50), unique=True, index=True)
    certificate_type = Column(String(50))  # valuation, inspection, assessment

    vehicle_make = Column(String(100))
    vehicle_model = Column(String(100))
    vehicle_reg = Column(String(20))
    vin = Column(String(17))

    result = Column(JSON)
    # NOTE: Column named "metadata" in Python would collide with
    # SQLAlchemy's reserved Base.metadata attribute and crash at
    # import time. Python attribute is `certificate_metadata`;
    # the actual DB column is still named "metadata".
    certificate_metadata = Column("metadata", JSON)

    pdf_url = Column(String(500))
    qr_code = Column(String(500))

    status = Column(String(20), default="active")  # active, expired, revoked
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(Date, nullable=True)

    user = relationship("UserProfile", back_populates="certificates")

    __table_args__ = (
        Index("idx_certificates_user_id", "user_id"),
        Index("idx_certificates_number", "certificate_number"),
        UniqueConstraint("certificate_number", name="uq_certificates_number"),
        {"schema": "public"},  # ← ADDED: Explicit schema
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "certificate_number": self.certificate_number,
            "certificate_type": self.certificate_type,
            "vehicle_make": self.vehicle_make,
            "vehicle_model": self.vehicle_model,
            "vehicle_reg": self.vehicle_reg,
            "vin": self.vin,
            "result": self.result,
            "metadata": self.certificate_metadata,
            "pdf_url": self.pdf_url,
            "qr_code": self.qr_code,
            "status": self.status,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
        }
