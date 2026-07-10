from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PaymentRequest(BaseModel):
    amount: float
    phone_number: str
    description: Optional[str] = None


class PaymentResponse(BaseModel):
    payment_id: str
    transaction_id: str
    status: str
    amount: float
    phone_number: str
    message: str


class PaymentStatus(BaseModel):
    payment_id: str
    transaction_id: str
    status: str
    amount: float
    phone_number: str
    completed_at: Optional[str] = None
