# app/models/inspection.py
# =============================================================================
# AUTO-V API - Inspection Model
# =============================================================================

import uuid
from sqlalchemy import Column, String, Integer, DateTime, Date, Text, JSON, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(PGUUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    inspector_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    inspection_type = Column(String(20))  # Standard, Premium, Express, AI, Virtual
    inspection_date = Column(Date, nullable=False)
    inspection_location = Column(String(255))

    engine_score = Column(Integer)
    transmission_score = Column(Integer)
    suspension_score = Column(Integer)
    brake_score = Column(Integer)
    paint_score = Column(Integer)
    interior_score = Column(Integer)
    tyre_depth = Column(Float)

    accident_history = Column(String(20))
    notes = Column(Text)
    images = Column(JSON)
    findings = Column(JSON)
    damage_assessment = Column(JSON)

    status = Column(String(20), default="pending")
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    vehicle = relationship("Vehicle", back_populates="inspections")
    inspector = relationship("UserProfile", back_populates="inspections")

    __table_args__ = (
        Index("idx_inspections_vehicle_id", "vehicle_id"),
        Index("idx_inspections_inspector_id", "inspector_id"),
        Index("idx_inspections_status", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "vehicle_id": str(self.vehicle_id),
            "inspector_id": str(self.inspector_id) if self.inspector_id else None,
            "inspection_type": self.inspection_type,
            "inspection_date": self.inspection_date.isoformat() if self.inspection_date else None,
            "engine_score": self.engine_score,
            "transmission_score": self.transmission_score,
            "suspension_score": self.suspension_score,
            "brake_score": self.brake_score,
            "paint_score": self.paint_score,
            "interior_score": self.interior_score,
            "accident_history": self.accident_history,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
