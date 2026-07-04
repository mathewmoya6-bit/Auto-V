# app/models/mileage.py
# =============================================================================
# AUTO-V API - Mileage Models
# =============================================================================

import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class VehicleCategory(Base):
    __tablename__ = "vehicle_categories"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    fuel_type = Column(String(50), nullable=False, default="Petrol")
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    variants = relationship("VehicleVariant", back_populates="category", cascade="all, delete-orphan")


class VehicleVariant(Base):
    __tablename__ = "vehicle_variants"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(PGUUID(as_uuid=True), ForeignKey("vehicle_categories.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(255), nullable=False)
    engine_class = Column(String(100), nullable=True)
    fixed_per_km = Column(Float, default=0)
    operating_per_km = Column(Float, default=0)
    total_per_km = Column(Float, default=0)
    initial_cost = Column(Float, default=0)
    year1 = Column(Float, default=0)
    year2 = Column(Float, default=0)
    year3 = Column(Float, default=0)
    year4 = Column(Float, default=0)
    year5 = Column(Float, default=0)
    components = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    category = relationship("VehicleCategory", back_populates="variants")


class Route(Base):
    __tablename__ = "routes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_city = Column(String(100), nullable=False, index=True)
    to_city = Column(String(100), nullable=False, index=True)
    km = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
