# app/models/certificate.py
# =============================================================================
# AUTO-V API - Certificate Model (Pydantic Native)
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Certificate(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    vehicle_id: uuid.UUID
    user_id: uuid.UUID
    
    certificate_number: str
    certificate_type: str  # e.g., "safety", "emissions", "registration"
    issue_date: datetime
    expiry_date: Optional[datetime] = None
    status: str = "active"  # active, expired, revoked
    
    document_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True
    }
