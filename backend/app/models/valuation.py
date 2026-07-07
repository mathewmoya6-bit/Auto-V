# app/models/valuation.py
# =============================================================================
# AUTO-V API - Valuation Model (Pydantic Native)
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class Valuation(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    vehicle_id: uuid.UUID
    user_id: uuid.UUID
    
    market_value: float
    currency: str = "USD"
    valuation_source: str  # e.g., "manual", "automated_api", "historical"
    raw_data: Optional[Dict[str, Any]] = None  # Storage for external API metadata
    status: str = "completed"  # pending, completed, failed
    
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True
    }

    def to_dict(self) -> dict:
        """Convert valuation object to a standard primitive dictionary."""
        return {
            "id": str(self.id),
            "vehicle_id": str(self.vehicle_id),
            "user_id": str(self.user_id),
            "market_value": self.market_value,
            "currency": self.currency,
            "valuation_source": self.valuation_source,
            "raw_data": self.raw_data,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
