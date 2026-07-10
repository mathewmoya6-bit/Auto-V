# backend/app/models/inspection.py
# =============================================================================
# Inspection Model
# =============================================================================

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base

class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True)
    
    registration_number = Column(String(20))
    make = Column(String(100))
    model = Column(String(100))
    year = Column(Integer)
    vin = Column(String(17))
    odometer = Column(Integer)
    
    inspection_type = Column(String(50))
    purpose = Column(String(100))
    region = Column(String(100))
    
    inspector_name = Column(String(255))
    inspector_credentials = Column(String(100))
    inspector_signature = Column(Text)
    
    condition_scores = Column(JSON, default={})
    issues = Column(JSON, default=[])
    
    kebs_score = Column(Float)
    kebs_status = Column(String(20))
    kebs_critical_failures = Column(JSON, default=[])
    kebs_results = Column(JSON, default={})
    
    overall_score = Column(Float)
    confidence_score = Column(Float)
    
    certificate_number = Column(String(50), unique=True)
    status = Column(String(20), default="pending")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
