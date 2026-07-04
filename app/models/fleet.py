# app/models/fleet.py
# =============================================================================
# AUTO-V API - Fleet Models
# =============================================================================

import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text, Numeric, BigInteger, Float,
    ForeignKey, Index, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Fleet(Base):
    __tablename__ = "fleets"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    fleet_code = Column(String(50), unique=True, index=True)

    total_vehicles = Column(Integer, default=0)
    active_vehicles = Column(Integer, default=0)
    total_drivers = Column(Integer, default=0)
    total_annual_km = Column(BigInteger, default=0)
    total_annual_cost = Column(Numeric(15, 2), default=0)
    average_cost_per_km = Column(Numeric(10, 4), default=0)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("UserProfile", back_populates="fleets")
    fleet_vehicles = relationship("FleetVehicle", back_populates="fleet", cascade="all, delete-orphan")
    fleet_drivers = relationship("FleetDriver", back_populates="fleet", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_fleets_owner_id", "owner_id"),
        Index("idx_fleets_is_active", "is_active"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id),
            "name": self.name,
            "fleet_code": self.fleet_code,
            "total_vehicles": self.total_vehicles,
            "active_vehicles": self.active_vehicles,
            "total_annual_km": self.total_annual_km,
            "total_annual_cost": float(self.total_annual_cost) if self.total_annual_cost else 0,
            "average_cost_per_km": float(self.average_cost_per_km) if self.average_cost_per_km else 0,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FleetVehicle(Base):
    __tablename__ = "fleet_vehicles"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id = Column(PGUUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False)
    vehicle_id = Column(PGUUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)

    assignment_status = Column(String(20), default="active")
    fleet_number = Column(String(50))
    current_mileage = Column(BigInteger)
    last_service_date = Column(Date)
    next_service_due = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    fleet = relationship("Fleet", back_populates="fleet_vehicles")
    vehicle = relationship("Vehicle", back_populates="fleet_vehicles")

    __table_args__ = (
        Index("idx_fleet_vehicles_fleet_id", "fleet_id"),
        UniqueConstraint("fleet_id", "vehicle_id", name="uq_fleet_vehicles"),
    )


class FleetDriver(Base):
    __tablename__ = "fleet_drivers"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id = Column(PGUUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    driver_code = Column(String(50), unique=True, index=True)
    license_number = Column(String(50))
    license_expiry = Column(Date)
    employment_status = Column(String(20), default="active")

    total_trips = Column(Integer, default=0)
    total_km = Column(BigInteger, default=0)
    safety_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    fleet = relationship("Fleet", back_populates="fleet_drivers")
    user = relationship("UserProfile")

    __table_args__ = (Index("idx_fleet_drivers_fleet_id", "fleet_id"),)
