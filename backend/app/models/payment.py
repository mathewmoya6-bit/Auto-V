# app/models/payment.py
# =============================================================================
# AUTO-V API - Payment Transaction Model (Pydantic Native)
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class Payment(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    claim_id: Optional[uuid.UUID] = None  # If tied to a MileageClaim
    
    amount: float
    currency: str = "USD"
    status: str = "pending"  # pending, completed, failed, refunded
    payment_method: str  # e.g., "stripe", "bank_transfer", "internal"
    transaction_reference: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None  # Gateway specific data
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True
    }
