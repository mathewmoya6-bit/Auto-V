# app/schemas/users.py
"""
MERGE this into your existing user schemas file — don't overwrite it.

IMPORTANT: check whether your file is actually named `users.py` (plural) or
something else. app/schemas/__init__.py currently does:

    from .user import UserProfile          # <-- singular, currently broken

If your real file is `users.py` (plural), fix that import line to:

    from .users import UserProfile

If your real file IS named `user.py` (singular) and simply doesn't have a
`UserProfile` class yet, add it there instead of creating this new file —
having both `user.py` and `users.py` would just create a second, worse
version of the same mismatch bug.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


# --- NEW: this is what app/schemas/__init__.py is trying to import ---------

class UserProfile(BaseModel):
    """
    Fuller profile view than UserResponse — TODO(integration): adjust fields
    to match whatever your actual User model/table has beyond the basics
    (e.g. phone, avatar_url, vehicle_count, member_since, etc.)
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
