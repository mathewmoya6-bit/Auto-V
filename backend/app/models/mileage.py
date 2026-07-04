# app/models/mileage.py
# =============================================================================
# AUTO-V API - Mileage Models (Aligned with Database Schema)
# =============================================================================

import uuid
from sqlalchemy import (
    Column, String, Boolean, Numeric, DateTime, Date, Text, JSON, BigInteger,
    ForeignKey, Index, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class VehicleCategory(Base):
    __tablename__ = "vehicle_categories"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    fuel_type = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    variants = relationship("VehicleVariant", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_vehicle_categories_active", "is_active"),
    )


class VehicleVariant(Base):
    __tablename__ = "vehicle_variants"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(PGUUID(as_uuid=True), ForeignKey("vehicle_categories.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(150), nullable=False)

    fixed_per_km = Column(Numeric(10, 4), default=0)
    operating_per_km = Column(Numeric(10, 4), default=0)
    total_per_km = Column(Numeric(10, 4), default=0)

    initial_cost = Column(Numeric(14, 2), default=0)
    year1 = Column(Numeric(14, 2), default=0)
    year2 = Column(Numeric(14, 2), default=0)
    year3 = Column(Numeric(14, 2), default=0)
    year4 = Column(Numeric(14, 2), default=0)
    year5 = Column(Numeric(14, 2), default=0)

    components = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category = relationship("VehicleCategory", back_populates="variants")

    __table_args__ = (
        Index("idx_vehicle_variants_category_id", "category_id"),
        Index("idx_vehicle_variants_active", "is_active"),
    )


class Route(Base):
    __tablename__ = "routes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_city = Column(String(150), nullable=False)
    to_city = Column(String(150), nullable=False)
    km = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("from_city", "to_city", name="uq_routes_from_to"),
        Index("idx_routes_active", "is_active"),
    )


class MileageClaim(Base):
    __tablename__ = "mileage_claims"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vehicle_id = Column(PGUUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)

    trip_date = Column(Date, nullable=False)
    start_location = Column(String(255))
    end_location = Column(String(255))
    distance_km = Column(Numeric(8, 2))
    vehicle_category = Column(String(50))
    rate_per_km = Column(Numeric(8, 2))
    claim_amount = Column(Numeric(10, 2))
    purpose = Column(String(100))
    notes = Column(Text)

    odometer_start = Column(BigInteger)
    odometer_end = Column(BigInteger)

    status = Column(String(20), default="pending")
    approved_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("UserProfile", foreign_keys=[user_id], back_populates="mileage_claims")
    approver = relationship("UserProfile", foreign_keys=[approved_by], back_populates="approved_mileage_claims")
    vehicle = relationship("Vehicle", foreign_keys=[vehicle_id], back_populates="mileage_claims")

    __table_args__ = (
        Index("idx_mileage_claims_user_id", "user_id"),
        Index("idx_mileage_claims_status", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "vehicle_id": str(self.vehicle_id) if self.vehicle_id else None,
            "trip_date": self.trip_date.isoformat() if self.trip_date else None,
            "start_location": self.start_location,
            "end_location": self.end_location,
            "distance_km": float(self.distance_km) if self.distance_km else 0,
            "rate_per_km": float(self.rate_per_km) if self.rate_per_km else 0,
            "claim_amount": float(self.claim_amount) if self.claim_amount else 0,
            "purpose": self.purpose,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
