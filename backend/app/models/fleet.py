# app/models/fleet.py
# =============================================================================
# AUTO-V API - Fleet Management Model (Pydantic Native)
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Fleet(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    manager_id: uuid.UUID  # Links to UserProfile.id
    name: str
    company_name: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True
    }
