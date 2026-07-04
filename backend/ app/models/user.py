# app/models/user.py
# =============================================================================
# AUTO-V API - User Model
# =============================================================================

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    supabase_user_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_active", "is_active"),
        Index("idx_users_supabase_id", "supabase_user_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "supabase_user_id": self.supabase_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    def to_public_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
        }

    def is_admin(self) -> bool:
        return self.role in ["admin", "super_admin"]

    def __repr__(self) -> str:
        return f"<UserProfile(id={self.id}, email={self.email}, role={self.role})>"
