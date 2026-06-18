# models.py – AUTO-V Database Models
# Uses SQLAlchemy 2.0 style (async-compatible)

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Numeric, Date, JSON,
    ForeignKey, CheckConstraint, UniqueConstraint, Index, Text, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import expression
import uuid
from datetime import datetime, date

Base = declarative_base()

# Helper for UUID columns
def generate_uuid():
    return str(uuid.uuid4())


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    full_name = Column(String)
    phone = Column(String)
    role = Column(String, default="user", server_default="user")
    first_login = Column(Boolean, default=True, server_default=expression.true())
    has_vehicle = Column(Boolean, default=False, server_default=expression.false())
    login_count = Column(Integer, default=1, server_default="1")
    valuation_count = Column(Integer, default=0, server_default="0")
    inspection_count = Column(Integer, default=0, server_default="0")
    assessment_count = Column(Integer, default=0, server_default="0")
    claim_count = Column(Integer, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    # Relationships
    service_requests = relationship("ServiceRequest", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    mileage_claims = relationship("MileageClaim", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="check_role"),
    )

    @validates("email")
    def validate_email(self, key, email):
        assert "@" in email, "Invalid email format"
        return email.lower()


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    
    service_type = Column(String, nullable=False)
    customer_type = Column(String)
    customer_name = Column(String)
    customer_id = Column(String)
    customer_phone = Column(String)
    customer_email = Column(String)
    company_name = Column(String)
    business_reg = Column(String)
    contact_person = Column(String)
    
    registration_number = Column(String)
    vin = Column(String)
    make = Column(String)
    model = Column(String)
    year = Column(Integer)
    odometer = Column(Integer)
    condition = Column(String)  # Excellent, Good, Fair, Poor
    accident_history = Column(String)  # None, Minor, Moderate, Major
    body_type = Column(String)
    engine_cc = Column(Integer)
    transmission = Column(String)  # Manual, Automatic, CVT, DCT
    fuel_type = Column(String)  # Petrol, Diesel, Hybrid, Electric, LPG
    location = Column(String)
    
    purpose = Column(String)
    purpose_data = Column(JSON)
    amount = Column(Numeric(10, 2))
    payment_status = Column(String, default="pending")
    status = Column(String, default="pending")
    
    inspection_type = Column(String)  # Standard, Premium, Express
    inspection_date = Column(Date)
    inspection_location = Column(String)
    inspection_notes = Column(String)
    
    valuation_methodology = Column(String)
    valuation_region = Column(String)
    
    image_count = Column(Integer, default=0)
    document_count = Column(Integer, default=0)
    document_verification = Column(String, default="Pending")
    image_urls = Column(JSON)
    document_urls = Column(JSON)
    inspector = Column(JSON, default={})
    inspection_scores = Column(JSON, default={})  # Detailed condition scores
    valuation_result = Column(JSON, default={})   # Full valuation result
    result = Column(JSON, default={})             # General result (for non-valuation/inspection)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("UserProfile", back_populates="service_requests")

    __table_args__ = (
        CheckConstraint("service_type IN ('instant', 'valuation', 'inspection', 'assessment', 'mileage', 'fleet', 'verification')", name="check_service_type"),
        CheckConstraint("customer_type IN ('individual', 'corporate')", name="check_customer_type"),
        CheckConstraint("payment_status IN ('pending', 'paid', 'failed', 'refunded')", name="check_payment_status"),
        CheckConstraint("status IN ('pending', 'assessor_review', 'quality_check', 'approved', 'completed', 'rejected', 'cancelled')", name="check_status"),
        CheckConstraint("condition IN ('Excellent', 'Good', 'Fair', 'Poor')", name="check_condition"),
        CheckConstraint("accident_history IN ('None', 'Minor', 'Moderate', 'Major')", name="check_accident_history"),
        CheckConstraint("transmission IN ('Manual', 'Automatic', 'CVT', 'DCT')", name="check_transmission"),
        CheckConstraint("fuel_type IN ('Petrol', 'Diesel', 'Hybrid', 'Electric', 'LPG')", name="check_fuel_type"),
        CheckConstraint("inspection_type IN ('Standard', 'Premium', 'Express')", name="check_inspection_type"),
        CheckConstraint("document_verification IN ('Pending', 'Verified', 'Failed')", name="check_doc_verification"),
        Index("idx_service_requests_user_id", "user_id"),
        Index("idx_service_requests_service_type", "service_type"),
        Index("idx_service_requests_status", "status"),
        Index("idx_service_requests_payment_status", "payment_status"),
        Index("idx_service_requests_created_at", "created_at"),
        Index("idx_service_requests_registration", "registration_number"),
        Index("idx_service_requests_purpose", "purpose"),
        Index("idx_service_requests_purpose_data", "purpose_data", postgresql_using="gin"),
        Index("idx_service_requests_result", "result", postgresql_using="gin"),
        Index("idx_service_requests_image_urls", "image_urls", postgresql_using="gin"),
        Index("idx_service_requests_document_urls", "document_urls", postgresql_using="gin"),
        Index("idx_service_requests_inspector", "inspector", postgresql_using="gin"),
        Index("idx_service_requests_inspection_scores", "inspection_scores", postgresql_using="gin"),
        Index("idx_service_requests_valuation_result", "valuation_result", postgresql_using="gin"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    service_type = Column(String, nullable=False)
    purpose = Column(String)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String, default="mpesa")
    status = Column(String, default="pending")
    reference = Column(String, unique=True)
    mpesa_phone = Column(String)
    transaction_id = Column(String)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    approved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    # Relationships
    user = relationship("UserProfile", back_populates="payments")
    approver = relationship("UserProfile", foreign_keys=[approved_by])

    __table_args__ = (
        CheckConstraint("service_type IN ('instant', 'valuation', 'inspection', 'assessment', 'mileage', 'fleet', 'verification')", name="check_service_type"),
        CheckConstraint("payment_method IN ('mpesa', 'card', 'bank', 'cash')", name="check_payment_method"),
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed', 'refunded')", name="check_status"),
        Index("idx_payments_user_id", "user_id"),
        Index("idx_payments_status", "status"),
        Index("idx_payments_service_type", "service_type"),
        Index("idx_payments_created_at", "created_at"),
        Index("idx_payments_reference", "reference"),
        UniqueConstraint("reference", name="uq_payments_reference"),
    )


class MileageClaim(Base):
    __tablename__ = "mileage_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    trip_date = Column(Date, nullable=False)
    start_location = Column(String)
    end_location = Column(String)
    distance_km = Column(Numeric(8, 2))
    vehicle_category = Column(String)
    rate_per_km = Column(Numeric(8, 2))
    claim_amount = Column(Numeric(10, 2))
    purpose = Column(String)
    status = Column(String, default="pending")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    approved_at = Column(DateTime(timezone=True))
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    user = relationship("UserProfile", back_populates="mileage_claims")
    approver = relationship("UserProfile", foreign_keys=[approved_by])

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected', 'paid')", name="check_status"),
        Index("idx_mileage_claims_user_id", "user_id"),
        Index("idx_mileage_claims_status", "status"),
        Index("idx_mileage_claims_trip_date", "trip_date"),
    )


class MileageRate(Base):
    __tablename__ = "mileage_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_category = Column(String, nullable=False)
    rate_per_km = Column(Numeric(8, 2), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    is_active = Column(Boolean, default=True, server_default=expression.true())
    description = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    __table_args__ = (
        Index("idx_mileage_rates_active", "is_active"),
        Index("idx_mileage_rates_effective", "effective_from", "effective_to"),
        Index("idx_mileage_rates_category", "vehicle_category"),
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_key = Column(String, unique=True, nullable=False)
    setting_value = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    __table_args__ = (
        Index("idx_system_settings_key", "setting_key"),
        UniqueConstraint("setting_key", name="uq_system_settings_key"),
    )
