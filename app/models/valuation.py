# app/models/valuation.py
# =============================================================================
# AUTO-V API - Valuation Model
# =============================================================================

import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Numeric, JSON, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Valuation(Base):
    __tablename__ = "valuations"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(PGUUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    valuation_type = Column(String(20), default="standard")  # instant, standard, premium

    market_value = Column(Numeric(12, 2))
    trade_in_value = Column(Numeric(12, 2))
    retail_value = Column(Numeric(12, 2))
    insurance_value = Column(Numeric(12, 2))
    forced_sale_value = Column(Numeric(12, 2))

    confidence_score = Column(Integer)
    condition_score = Column(Float)

    purpose = Column(String(100))
    region = Column(String(50))
    factors = Column(JSON)
    ai_analysis = Column(JSON)

    status = Column(String(20), default="draft")  # draft, completed, verified
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    vehicle = relationship("Vehicle", back_populates="valuations")
    user = relationship("UserProfile", back_populates="valuations")

    __table_args__ = (
        Index("idx_valuations_vehicle_id", "vehicle_id"),
        Index("idx_valuations_user_id", "user_id"),
        Index("idx_valuations_status", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "vehicle_id": str(self.vehicle_id),
            "user_id": str(self.user_id),
            "valuation_type": self.valuation_type,
            "market_value": float(self.market_value) if self.market_value else None,
            "trade_in_value": float(self.trade_in_value) if self.trade_in_value else None,
            "retail_value": float(self.retail_value) if self.retail_value else None,
            "insurance_value": float(self.insurance_value) if self.insurance_value else None,
            "confidence_score": self.confidence_score,
            "purpose": self.purpose,
            "region": self.region,
            "status": self.status,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
