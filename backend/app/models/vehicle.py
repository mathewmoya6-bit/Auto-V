# app/models/vehicle.py
# =============================================================================
# AUTO-V API - Vehicle, VehicleImage, VINScan Models
# =============================================================================

import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON, Float, BigInteger,
    ForeignKey, Index, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)

    vin = Column(String(17), unique=True, nullable=False, index=True)
    registration_number = Column(String(20), unique=True, index=True)
    make = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)
    vehicle_type = Column(String(50), default="Car")

    body_type = Column(String(50))
    engine_cc = Column(Integer)
    transmission = Column(String(20))
    fuel_type = Column(String(20))
    odometer = Column(BigInteger)
    color = Column(String(50))

    condition = Column(String(20))
    accident_history = Column(String(20))
    owners = Column(Integer, default=1)

    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # FIXED: Added explicit foreign_keys to relationships
    owner = relationship(
        "UserProfile",
        foreign_keys=[user_id],  # ← ADDED: Explicit
        back_populates="vehicles"
    )
    
    images = relationship("VehicleImage", back_populates="vehicle", cascade="all, delete-orphan")
    valuations = relationship("Valuation", back_populates="vehicle", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="vehicle", cascade="all, delete-orphan")
    
    mileage_claims = relationship(
        "MileageClaim",
        foreign_keys="MileageClaim.vehicle_id",  # ← ADDED: Explicit
        back_populates="vehicle"
    )
    
    fleet_vehicles = relationship("FleetVehicle", back_populates="vehicle", cascade="all, delete-orphan")
    vin_scans = relationship("VINScan", back_populates="vehicle")

    __table_args__ = (
        Index("idx_vehicles_vin", "vin"),
        Index("idx_vehicles_registration", "registration_number"),
        Index("idx_vehicles_user_id", "user_id"),
        UniqueConstraint("vin", name="uq_vehicles_vin"),
        {"schema": "public"},  # ← ADDED: Explicit schema
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "vin": self.vin,
            "registration_number": self.registration_number,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "vehicle_type": self.vehicle_type,
            "odometer": self.odometer,
            "condition": self.condition,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VehicleImage(Base):
    __tablename__ = "vehicle_images"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(PGUUID(as_uuid=True), ForeignKey("public.vehicles.id", ondelete="CASCADE"), nullable=False)

    slot = Column(String(50), nullable=False)  # front, rear, left, right, interior, engine, vin
    image_url = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False)
    ai_analyzed = Column(Boolean, default=False)
    ai_damage_detected = Column(Boolean, default=False)
    ai_confidence = Column(Float)
    ai_analysis_data = Column(JSON)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    vehicle = relationship("Vehicle", back_populates="images")

    __table_args__ = (
        Index("idx_vehicle_images_vehicle_id", "vehicle_id"),
        UniqueConstraint("vehicle_id", "slot", name="uq_vehicle_images_slot"),
        {"schema": "public"},  # ← ADDED: Explicit schema
    )


class VINScan(Base):
    __tablename__ = "vin_scans"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    vehicle_id = Column(PGUUID(as_uuid=True), ForeignKey("public.vehicles.id", ondelete="SET NULL"), nullable=True)

    vin = Column(String(17), nullable=False, index=True)
    image_url = Column(String(500))
    confidence = Column(Float)
    validation_result = Column(JSON)
    vehicle_data = Column(JSON)
    status = Column(String(20), default="pending")  # pending, verified, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # FIXED: Added explicit foreign_keys
    vehicle = relationship(
        "Vehicle",
        foreign_keys=[vehicle_id],  # ← ADDED: Explicit
        back_populates="vin_scans"
    )

    __table_args__ = (
        Index("idx_vin_scans_vin", "vin"),
        Index("idx_vin_scans_user_id", "user_id"),
        {"schema": "public"},  # ← ADDED: Explicit schema
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "vin": self.vin,
            "confidence": self.confidence,
            "vehicle_data": self.vehicle_data,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
