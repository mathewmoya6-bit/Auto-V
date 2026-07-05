# backend/app/models/valuation.py
# =============================================================================
# Valuation Model
# =============================================================================

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base

class Valuation(Base):
    __tablename__ = "valuations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True)
    
    make = Column(String(100))
    model = Column(String(100))
    year = Column(Integer)
    engine_capacity = Column(Integer)
    fuel_type = Column(String(50))
    transmission = Column(String(50))
    body_type = Column(String(50))
    body_color = Column(String(50))
    mileage = Column(Integer)
    condition = Column(String(20))
    accident_history = Column(String(50))
    location = Column(String(100))
    previous_owners = Column(Integer)
    usage_type = Column(String(50))
    
    market_value = Column(Float)
    insurance_value = Column(Float)
    trade_in_value = Column(Float)
    forced_sale_value = Column(Float)
    confidence_score = Column(Float)
    
    certificate_number = Column(String(50), unique=True)
    status = Column(String(20), default="completed")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
