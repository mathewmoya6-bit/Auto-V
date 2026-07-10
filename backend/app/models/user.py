# app/models/user.py
# =============================================================================
# AUTO-V API - User Profile Model (Pydantic Native)
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

class UserProfile(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "user"
    company_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    supabase_user_id: str  # Linked to auth.users.id in Supabase

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

    def to_public_dict(self) -> dict:
        """Return public user data (omitting sensitive flags if necessary)"""
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

    def to_dict(self) -> dict:
        """Return all user data formatted as a primitive dictionary"""
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role,
            "company_name": self.company_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "supabase_user_id": self.supabase_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
