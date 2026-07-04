import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    role = Column(String(50), default="user", nullable=False)
    company_name = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    supabase_user_id = Column(String(255), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # ===========================
    # Relationships
    # ===========================

    vehicles = relationship(
        "Vehicle",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    valuations = relationship(
        "Valuation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    inspections = relationship(
        "Inspection",
        back_populates="inspector",
    )

    mileage_claims = relationship(
        "MileageClaim",
        foreign_keys="MileageClaim.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    approved_mileage_claims = relationship(
        "MileageClaim",
        foreign_keys="MileageClaim.approved_by",
        back_populates="approver",  # ← FIXED: Added back_populates
    )

    fleets = relationship(
        "Fleet",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    certificates = relationship(
        "Certificate",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    payments = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_active", "is_active"),
        {"schema": "public"},  # ← ADDED: Explicit schema
    )

    def is_admin(self):
        return self.role in ("admin", "super_admin")
