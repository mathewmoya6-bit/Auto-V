# app/models/user.py
# =============================================================================
# AUTO-V API - User Model
# =============================================================================
# SQLAlchemy model for user profiles stored in Supabase PostgreSQL.
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserProfile(Base):
    """
    User Profile model for storing user information.
    
    This model is used to store user profiles that are synced with Supabase Auth.
    When a user logs in via Supabase, their profile is created/updated in this table.
    """
    __tablename__ = "users"

    # ─── Primary Key ──────────────────────────────────────────────────
    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Unique user identifier (UUID)"
    )

    # ─── User Information ────────────────────────────────────────────
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User's email address (unique)"
    )

    full_name = Column(
        String(255),
        nullable=True,
        doc="User's full name"
    )

    role = Column(
        String(50),
        default="user",
        nullable=False,
        doc="User role: user, admin, super_admin, inspector, valuer"
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the user account is active"
    )

    # ─── Supabase Auth ID ────────────────────────────────────────────
    supabase_user_id = Column(
        String(255),
        nullable=True,
        index=True,
        doc="Supabase Auth user ID for syncing"
    )

    # ─── Timestamps ──────────────────────────────────────────────────
    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the user was created"
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when the user was last updated"
    )

    last_login = Column(
        DateTime,
        nullable=True,
        doc="Timestamp of the user's last login"
    )

    # ─── Metadata ─────────────────────────────────────────────────────
    metadata = Column(
        String,
        nullable=True,
        doc="Additional user metadata (JSON string)"
    )

    # ─── Table Indexes ──────────────────────────────────────────────
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_active", "is_active"),
        Index("idx_users_supabase_id", "supabase_user_id"),
    )

    # ─── Methods ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        Convert the user model to a dictionary.
        
        Returns:
            dict: User data as a dictionary
        """
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
        """
        Convert the user model to a public dictionary (limited fields).
        
        Returns:
            dict: Limited user data for public API responses
        """
        return {
            "id": str(self.id) if self.id else None,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
        }

    def is_admin(self) -> bool:
        """Check if the user has admin privileges."""
        return self.role in ["admin", "super_admin"]

    def is_super_admin(self) -> bool:
        """Check if the user has super admin privileges."""
        return self.role == "super_admin"

    def is_active_user(self) -> bool:
        """Check if the user account is active."""
        return self.is_active is True

    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<UserProfile(id={self.id}, email={self.email}, role={self.role})>"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.full_name or self.email} ({self.role})"


# ─── Pydantic Schemas for User ──────────────────────────────────────

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    role: str = Field(default="user", description="User role")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=6, description="User's password")


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    full_name: Optional[str] = Field(None, description="User's full name")
    role: Optional[str] = Field(None, description="User role")
    is_active: Optional[bool] = Field(None, description="Whether the user is active")


class UserResponse(UserBase):
    """Schema for user response."""
    id: str = Field(..., description="User's UUID")
    is_active: bool = Field(..., description="Whether the user is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True
