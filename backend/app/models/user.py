# app/models/user.py
# =============================================================================
# AUTO-V API - User Models
# =============================================================================

import uuid
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Index, func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    phone = Column(String(50))
    role = Column(String(50), nullable=False, default="user")
    company_name = Column(String(255))
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    supabase_user_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True))

    # Relationships
    vehicles = relationship("Vehicle", foreign_keys="Vehicle.user_id", back_populates="owner")
    mileage_claims = relationship("MileageClaim", foreign_keys="MileageClaim.user_id", back_populates="user")
    approved_mileage_claims = relationship("MileageClaim", foreign_keys="MileageClaim.approved_by", back_populates="approver")
    vin_scans = relationship("VINScan", foreign_keys="VINScan.user_id", back_populates="user")
    
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_active", "is_active"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role,
            "company_name": self.company_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
