# app/models/user.py
# =============================================================================
# AUTO-V API - User Model
# =============================================================================

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
    role = Column(String(50), default="user", nullable=False)  # user, admin, super_admin, inspector, valuer, fleet_manager, assessor
    company_name = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    supabase_user_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    vehicles = relationship("Vehicle", back_populates="owner", cascade="all, delete-orphan")
    valuations = relationship("Valuation", back_populates="user", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="inspector")
    
    # FIXED: Added foreign_keys to specify which FK to use
    mileage_claims = relationship(
        "MileageClaim",
        back_populates="user",
        foreign_keys="MileageClaim.user_id",  # Explicitly tell SQLAlchemy which FK
        cascade="all, delete-orphan"
    )
    
    # Added: Relationship for claims this user approved
    approved_mileage_claims = relationship(
        "MileageClaim",
        back_populates="approver",
        foreign_keys="MileageClaim.approved_by",
        cascade="all, delete-orphan"
    )
    
    fleets = relationship("Fleet", back_populates="owner", cascade="all, delete-orphan")
    certificates = relationship("Certificate", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_active", "is_active"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role,
            "company_name": self.company_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    def to_public_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role
        }

    def is_admin(self) -> bool:
        return self.role in ("admin", "super_admin")
