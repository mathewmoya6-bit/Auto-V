# ============================================================
# models.py – AUTO-V Database Models
# Uses SQLAlchemy 2.0 style (async-compatible)
# ============================================================

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Numeric, Date, JSON,
    ForeignKey, CheckConstraint, UniqueConstraint, Index, Text, func,
    Float, BigInteger, Enum as SQLEnum, Table, MetaData
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates, backref, declarative_mixin
from sqlalchemy.sql import expression
import uuid
from datetime import datetime, date
import enum

# ─── Base Class ──────────────────────────────────────────────────

Base = declarative_base()
metadata = Base.metadata

# Helper for UUID columns
def generate_uuid():
    return str(uuid.uuid4())


# ─── ENUMS ──────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    INSPECTOR = "inspector"
    VALUER = "valuer"
    FLEET_MANAGER = "fleet_manager"
    ASSESSOR = "assessor"


class ServiceType(str, enum.Enum):
    INSTANT = "instant"
    VALUATION = "valuation"
    INSPECTION = "inspection"
    ASSESSMENT = "assessment"
    MILEAGE = "mileage"
    FLEET = "fleet"
    VERIFICATION = "verification"
    CERTIFICATE = "certificate"
    REPORT = "report"


class CustomerType(str, enum.Enum):
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"
    GOVERNMENT = "government"
    DEALER = "dealer"
    FLEET = "fleet"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class ServiceStatus(str, enum.Enum):
    PENDING = "pending"
    ASSESSOR_REVIEW = "assessor_review"
    QUALITY_CHECK = "quality_check"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    IN_PROGRESS = "in_progress"
    DRAFT = "draft"
    EXPIRED = "expired"


class VehicleCondition(str, enum.Enum):
    EXCELLENT = "Excellent"
    VERY_GOOD = "Very Good"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"


class AccidentHistory(str, enum.Enum):
    NONE = "None"
    MINOR = "Minor"
    MODERATE = "Moderate"
    MAJOR = "Major"
    WRITE_OFF = "WriteOff"


class TransmissionType(str, enum.Enum):
    MANUAL = "Manual"
    AUTOMATIC = "Automatic"
    CVT = "CVT"
    DCT = "DCT"
    SEMI_AUTOMATIC = "Semi-Automatic"


class FuelType(str, enum.Enum):
    PETROL = "Petrol"
    DIESEL = "Diesel"
    HYBRID = "Hybrid"
    ELECTRIC = "Electric"
    LPG = "LPG"
    CNG = "CNG"


class InspectionType(str, enum.Enum):
    STANDARD = "Standard"
    PREMIUM = "Premium"
    EXPRESS = "Express"
    AI = "AI"
    VIRTUAL = "Virtual"


class PaymentMethod(str, enum.Enum):
    MPESA = "mpesa"
    CARD = "card"
    BANK = "bank"
    CASH = "cash"
    CRYPTO = "crypto"
    STIPE = "stripe"


class DocumentVerificationStatus(str, enum.Enum):
    PENDING = "Pending"
    VERIFIED = "Verified"
    FAILED = "Failed"
    REVIEW = "Review"
    EXPIRED = "Expired"


class VehicleType(str, enum.Enum):
    CAR = "Car"
    SUV = "SUV"
    PICKUP = "Pickup"
    TRUCK = "Truck"
    VAN = "Van"
    BUS = "Bus"
    MOTORCYCLE = "Motorcycle"
    TRICYCLE = "Tricycle"
    TRAILER = "Trailer"


# ─── Mixins ─────────────────────────────────────────────────────

@declarative_mixin
class TimestampMixin:
    """Mixin for timestamp fields."""
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())


@declarative_mixin
class SoftDeleteMixin:
    """Mixin for soft delete."""
    is_deleted = Column(Boolean, default=False, server_default=expression.false())
    deleted_at = Column(DateTime(timezone=True))


# ─── USER PROFILE ─────────────────────────────────────────────

class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255))
    full_name = Column(String(255))
    phone = Column(String(50))
    role = Column(String(50), default=UserRole.USER.value, server_default=UserRole.USER.value)
    
    # Profile fields
    first_login = Column(Boolean, default=True, server_default=expression.true())
    has_vehicle = Column(Boolean, default=False, server_default=expression.false())
    login_count = Column(Integer, default=1, server_default="1")
    valuation_count = Column(Integer, default=0, server_default="0")
    inspection_count = Column(Integer, default=0, server_default="0")
    assessment_count = Column(Integer, default=0, server_default="0")
    claim_count = Column(Integer, default=0, server_default="0")
    
    # Business fields
    company_name = Column(String(255))
    business_reg = Column(String(100))
    tax_id = Column(String(50))
    
    # Status
    is_active = Column(Boolean, default=True, server_default=expression.true())
    is_verified = Column(Boolean, default=False, server_default=expression.false())
    last_login = Column(DateTime(timezone=True))
    last_ip = Column(String(45))
    
    # Relationships
    service_requests = relationship("ServiceRequest", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    mileage_claims = relationship("MileageClaim", back_populates="user", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="owner", cascade="all, delete-orphan")
    valuations = relationship("Valuation", back_populates="user", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="inspector")
    vin_scans = relationship("VINScan", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    certificates = relationship("Certificate", back_populates="user", cascade="all, delete-orphan")
    fleets = relationship("Fleet", back_populates="owner", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(f"role IN ('{UserRole.USER.value}', '{UserRole.ADMIN.value}', '{UserRole.SUPER_ADMIN.value}', '{UserRole.INSPECTOR.value}', '{UserRole.VALUER.value}', '{UserRole.FLEET_MANAGER.value}', '{UserRole.ASSESSOR.value}')", name="check_role"),
        Index("idx_user_profiles_email", "email"),
        Index("idx_user_profiles_role", "role"),
        Index("idx_user_profiles_created_at", "created_at"),
        Index("idx_user_profiles_phone", "phone"),
    )

    @validates("email")
    def validate_email(self, key, email):
        assert "@" in email, "Invalid email format"
        return email.lower()

    @validates("phone")
    def validate_phone(self, key, phone):
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if len(phone) < 10:
                raise ValueError("Phone number must be at least 10 digits")
        return phone

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role,
            "first_login": self.first_login,
            "has_vehicle": self.has_vehicle,
            "login_count": self.login_count,
            "valuation_count": self.valuation_count,
            "inspection_count": self.inspection_count,
            "assessment_count": self.assessment_count,
            "claim_count": self.claim_count,
            "company_name": self.company_name,
            "business_reg": self.business_reg,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# ─── VEHICLE ────────────────────────────────────────────────────

class Vehicle(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    
    # Vehicle Identification
    vin = Column(String(17), unique=True, nullable=False, index=True)
    registration_number = Column(String(20), unique=True, index=True)
    make = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)
    vehicle_type = Column(String(50), default=VehicleType.CAR.value)
    
    # Specifications
    body_type = Column(String(50))
    engine_cc = Column(Integer)
    transmission = Column(String(20))
    fuel_type = Column(String(20))
    odometer = Column(BigInteger)
    color = Column(String(50))
    
    # Condition
    condition = Column(String(20))
    accident_history = Column(String(20))
    service_history = Column(String(20))
    owners = Column(Integer, default=1)
    usage_type = Column(String(20))
    import_status = Column(String(20))
    warranty_status = Column(String(20))
    modifications = Column(Text)
    notes = Column(Text)
    
    # Additional
    is_active = Column(Boolean, default=True, server_default=expression.true())
    is_verified = Column(Boolean, default=False, server_default=expression.false())
    verified_at = Column(DateTime(timezone=True))
    
    # Relationships
    owner = relationship("UserProfile", back_populates="vehicles")
    images = relationship("VehicleImage", back_populates="vehicle", cascade="all, delete-orphan")
    valuations = relationship("Valuation", back_populates="vehicle", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="vehicle", cascade="all, delete-orphan")
    vin_scans = relationship("VINScan", back_populates="vehicle")
    service_requests = relationship("ServiceRequest", back_populates="vehicle_ref")
    mileage_claims = relationship("MileageClaim", back_populates="vehicle")
    fleet_vehicles = relationship("FleetVehicle", back_populates="vehicle", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(f"condition IN ('{VehicleCondition.EXCELLENT.value}', '{VehicleCondition.VERY_GOOD.value}', '{VehicleCondition.GOOD.value}', '{VehicleCondition.FAIR.value}', '{VehicleCondition.POOR.value}')", name="check_condition"),
        CheckConstraint(f"accident_history IN ('{AccidentHistory.NONE.value}', '{AccidentHistory.MINOR.value}', '{AccidentHistory.MODERATE.value}', '{AccidentHistory.MAJOR.value}', '{AccidentHistory.WRITE_OFF.value}')", name="check_accident_history"),
        CheckConstraint(f"transmission IN ('{TransmissionType.MANUAL.value}', '{TransmissionType.AUTOMATIC.value}', '{TransmissionType.CVT.value}', '{TransmissionType.DCT.value}', '{TransmissionType.SEMI_AUTOMATIC.value}')", name="check_transmission"),
        CheckConstraint(f"fuel_type IN ('{FuelType.PETROL.value}', '{FuelType.DIESEL.value}', '{FuelType.HYBRID.value}', '{FuelType.ELECTRIC.value}', '{FuelType.LPG.value}', '{FuelType.CNG.value}')", name="check_fuel_type"),
        CheckConstraint(f"vehicle_type IN ('{VehicleType.CAR.value}', '{VehicleType.SUV.value}', '{VehicleType.PICKUP.value}', '{VehicleType.TRUCK.value}', '{VehicleType.VAN.value}', '{VehicleType.BUS.value}', '{VehicleType.MOTORCYCLE.value}', '{VehicleType.TRICYCLE.value}', '{VehicleType.TRAILER.value}')", name="check_vehicle_type"),
        Index("idx_vehicles_vin", "vin"),
        Index("idx_vehicles_registration", "registration_number"),
        Index("idx_vehicles_make_model", "make", "model"),
        Index("idx_vehicles_user_id", "user_id"),
        Index("idx_vehicles_created_at", "created_at"),
        Index("idx_vehicles_vehicle_type", "vehicle_type"),
        UniqueConstraint("vin", name="uq_vehicles_vin"),
        UniqueConstraint("registration_number", name="uq_vehicles_registration"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "vin": self.vin,
            "registration_number": self.registration_number,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "vehicle_type": self.vehicle_type,
            "body_type": self.body_type,
            "engine_cc": self.engine_cc,
            "transmission": self.transmission,
            "fuel_type": self.fuel_type,
            "odometer": self.odometer,
            "color": self.color,
            "condition": self.condition,
            "accident_history": self.accident_history,
            "service_history": self.service_history,
            "owners": self.owners,
            "usage_type": self.usage_type,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# ─── VEHICLE IMAGE ─────────────────────────────────────────────

class VehicleImage(Base):
    __tablename__ = "vehicle_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    
    slot = Column(String(50), nullable=False)  # front, rear, left, right, interior, engine, vin
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    is_primary = Column(Boolean, default=False, server_default=expression.false())
    order = Column(Integer, default=0)
    
    # Metadata
    file_name = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(50))
    width = Column(Integer)
    height = Column(Integer)
    
    # AI Analysis
    ai_analyzed = Column(Boolean, default=False, server_default=expression.false())
    ai_damage_detected = Column(Boolean, default=False)
    ai_confidence = Column(Float)
    ai_analysis_data = Column(JSON)
    
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="images")

    __table_args__ = (
        Index("idx_vehicle_images_vehicle_id", "vehicle_id"),
        Index("idx_vehicle_images_slot", "slot"),
        Index("idx_vehicle_images_is_primary", "is_primary"),
        UniqueConstraint("vehicle_id", "slot", name="uq_vehicle_images_slot"),
        Index("idx_vehicle_images_ai_analyzed", "ai_analyzed"),
        Index("idx_vehicle_images_ai_analysis_data", "ai_analysis_data", postgresql_using="gin"),
    )


# ─── SERVICE REQUEST ──────────────────────────────────────────

class ServiceRequest(Base, TimestampMixin):
    __tablename__ = "service_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"))
    
    # Service Details
    service_type = Column(String(50), nullable=False)
    customer_type = Column(String(20))
    customer_name = Column(String(255))
    customer_id = Column(String(100))
    customer_phone = Column(String(50))
    customer_email = Column(String(255))
    company_name = Column(String(255))
    business_reg = Column(String(100))
    contact_person = Column(String(255))
    
    # Vehicle Details
    registration_number = Column(String(20))
    vin = Column(String(17))
    make = Column(String(100))
    model = Column(String(100))
    year = Column(Integer)
    odometer = Column(BigInteger)
    condition = Column(String(20))
    accident_history = Column(String(20))
    body_type = Column(String(50))
    engine_cc = Column(Integer)
    transmission = Column(String(20))
    fuel_type = Column(String(20))
    location = Column(String(255))
    
    # Service Data
    purpose = Column(String(100))
    purpose_data = Column(JSON)
    amount = Column(Numeric(10, 2))
    payment_status = Column(String(20), default="pending")
    status = Column(String(30), default="pending")
    
    # Inspection Specific
    inspection_type = Column(String(20))
    inspection_date = Column(Date)
    inspection_location = Column(String(255))
    inspection_notes = Column(Text)
    
    # Valuation Specific
    valuation_methodology = Column(String(50))
    valuation_region = Column(String(50))
    
    # Results
    image_count = Column(Integer, default=0)
    document_count = Column(Integer, default=0)
    document_verification = Column(String(20), default="Pending")
    image_urls = Column(JSON)
    document_urls = Column(JSON)
    inspector = Column(JSON, default={})
    inspection_scores = Column(JSON, default={})
    valuation_result = Column(JSON, default={})
    result = Column(JSON, default={})
    
    # Timestamps
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("UserProfile", back_populates="service_requests")
    vehicle_ref = relationship("Vehicle", back_populates="service_requests")
    payments = relationship("Payment", back_populates="service_request")
    certificates = relationship("Certificate", back_populates="service_request")

    __table_args__ = (
        CheckConstraint(f"service_type IN ('{ServiceType.INSTANT.value}', '{ServiceType.VALUATION.value}', '{ServiceType.INSPECTION.value}', '{ServiceType.ASSESSMENT.value}', '{ServiceType.MILEAGE.value}', '{ServiceType.FLEET.value}', '{ServiceType.VERIFICATION.value}', '{ServiceType.CERTIFICATE.value}', '{ServiceType.REPORT.value}')", name="check_service_type"),
        CheckConstraint(f"customer_type IN ('{CustomerType.INDIVIDUAL.value}', '{CustomerType.CORPORATE.value}', '{CustomerType.GOVERNMENT.value}', '{CustomerType.DEALER.value}', '{CustomerType.FLEET.value}')", name="check_customer_type"),
        CheckConstraint(f"payment_status IN ('{PaymentStatus.PENDING.value}', '{PaymentStatus.PROCESSING.value}', '{PaymentStatus.COMPLETED.value}', '{PaymentStatus.FAILED.value}', '{PaymentStatus.REFUNDED.value}', '{PaymentStatus.CANCELLED.value}')", name="check_payment_status"),
        CheckConstraint(f"status IN ('{ServiceStatus.PENDING.value}', '{ServiceStatus.ASSESSOR_REVIEW.value}', '{ServiceStatus.QUALITY_CHECK.value}', '{ServiceStatus.APPROVED.value}', '{ServiceStatus.COMPLETED.value}', '{ServiceStatus.REJECTED.value}', '{ServiceStatus.CANCELLED.value}', '{ServiceStatus.IN_PROGRESS.value}', '{ServiceStatus.DRAFT.value}', '{ServiceStatus.EXPIRED.value}')", name="check_status"),
        CheckConstraint(f"condition IN ('{VehicleCondition.EXCELLENT.value}', '{VehicleCondition.VERY_GOOD.value}', '{VehicleCondition.GOOD.value}', '{VehicleCondition.FAIR.value}', '{VehicleCondition.POOR.value}')", name="check_condition"),
        CheckConstraint(f"accident_history IN ('{AccidentHistory.NONE.value}', '{AccidentHistory.MINOR.value}', '{AccidentHistory.MODERATE.value}', '{AccidentHistory.MAJOR.value}', '{AccidentHistory.WRITE_OFF.value}')", name="check_accident_history"),
        CheckConstraint(f"transmission IN ('{TransmissionType.MANUAL.value}', '{TransmissionType.AUTOMATIC.value}', '{TransmissionType.CVT.value}', '{TransmissionType.DCT.value}', '{TransmissionType.SEMI_AUTOMATIC.value}')", name="check_transmission"),
        CheckConstraint(f"fuel_type IN ('{FuelType.PETROL.value}', '{FuelType.DIESEL.value}', '{FuelType.HYBRID.value}', '{FuelType.ELECTRIC.value}', '{FuelType.LPG.value}', '{FuelType.CNG.value}')", name="check_fuel_type"),
        CheckConstraint(f"inspection_type IN ('{InspectionType.STANDARD.value}', '{InspectionType.PREMIUM.value}', '{InspectionType.EXPRESS.value}', '{InspectionType.AI.value}', '{InspectionType.VIRTUAL.value}')", name="check_inspection_type"),
        CheckConstraint(f"document_verification IN ('{DocumentVerificationStatus.PENDING.value}', '{DocumentVerificationStatus.VERIFIED.value}', '{DocumentVerificationStatus.FAILED.value}', '{DocumentVerificationStatus.REVIEW.value}', '{DocumentVerificationStatus.EXPIRED.value}')", name="check_doc_verification"),
        Index("idx_service_requests_user_id", "user_id"),
        Index("idx_service_requests_service_type", "service_type"),
        Index("idx_service_requests_status", "status"),
        Index("idx_service_requests_payment_status", "payment_status"),
        Index("idx_service_requests_created_at", "created_at"),
        Index("idx_service_requests_registration", "registration_number"),
        Index("idx_service_requests_vin", "vin"),
        Index("idx_service_requests_vehicle_id", "vehicle_id"),
        Index("idx_service_requests_purpose_data", "purpose_data", postgresql_using="gin"),
        Index("idx_service_requests_result", "result", postgresql_using="gin"),
        Index("idx_service_requests_image_urls", "image_urls", postgresql_using="gin"),
        Index("idx_service_requests_document_urls", "document_urls", postgresql_using="gin"),
        Index("idx_service_requests_inspector", "inspector", postgresql_using="gin"),
        Index("idx_service_requests_inspection_scores", "inspection_scores", postgresql_using="gin"),
        Index("idx_service_requests_valuation_result", "valuation_result", postgresql_using="gin"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "vehicle_id": str(self.vehicle_id) if self.vehicle_id else None,
            "service_type": self.service_type,
            "customer_type": self.customer_type,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_email": self.customer_email,
            "registration_number": self.registration_number,
            "vin": self.vin,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "odometer": self.odometer,
            "condition": self.condition,
            "accident_history": self.accident_history,
            "purpose": self.purpose,
            "amount": float(self.amount) if self.amount else None,
            "payment_status": self.payment_status,
            "status": self.status,
            "image_count": self.image_count,
            "document_count": self.document_count,
            "document_verification": self.document_verification,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


# ─── PAYMENT ────────────────────────────────────────────────────

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    service_type = Column(String(50), nullable=False)
    service_request_id = Column(UUID(as_uuid=True), ForeignKey("service_requests.id", ondelete="SET NULL"))
    
    # Payment Details
    purpose = Column(String(100))
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(20), default="mpesa")
    status = Column(String(20), default="pending")
    reference = Column(String(50), unique=True)
    
    # M-Pesa Details
    mpesa_phone = Column(String(50))
    transaction_id = Column(String(100))
    checkout_request_id = Column(String(100))
    merchant_request_id = Column(String(100))
    mpesa_receipt = Column(String(100))
    mpesa_result_code = Column(String(10))
    mpesa_result_desc = Column(String(255))
    payment_data = Column(JSON)
    
    # Approval
    approved_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    approved_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("UserProfile", back_populates="payments")
    approver = relationship("UserProfile", foreign_keys=[approved_by])
    service_request = relationship("ServiceRequest", back_populates="payments")

    __table_args__ = (
        CheckConstraint(f"service_type IN ('{ServiceType.INSTANT.value}', '{ServiceType.VALUATION.value}', '{ServiceType.INSPECTION.value}', '{ServiceType.ASSESSMENT.value}', '{ServiceType.MILEAGE.value}', '{ServiceType.FLEET.value}', '{ServiceType.VERIFICATION.value}', '{ServiceType.CERTIFICATE.value}', '{ServiceType.REPORT.value}')", name="check_service_type"),
        CheckConstraint(f"payment_method IN ('{PaymentMethod.MPESA.value}', '{PaymentMethod.CARD.value}', '{PaymentMethod.BANK.value}', '{PaymentMethod.CASH.value}', '{PaymentMethod.CRYPTO.value}', '{PaymentMethod.STIPE.value}')", name="check_payment_method"),
        CheckConstraint(f"status IN ('{PaymentStatus.PENDING.value}', '{PaymentStatus.PROCESSING.value}', '{PaymentStatus.COMPLETED.value}', '{PaymentStatus.FAILED.value}', '{PaymentStatus.REFUNDED.value}', '{PaymentStatus.CANCELLED.value}', '{PaymentStatus.DISPUTED.value}')", name="check_status"),
        Index("idx_payments_user_id", "user_id"),
        Index("idx_payments_status", "status"),
        Index("idx_payments_service_type", "service_type"),
        Index("idx_payments_created_at", "created_at"),
        Index("idx_payments_reference", "reference"),
        Index("idx_payments_checkout_request_id", "checkout_request_id"),
        Index("idx_payments_transaction_id", "transaction_id"),
        Index("idx_payments_mpesa_receipt", "mpesa_receipt"),
        UniqueConstraint("reference", name="uq_payments_reference"),
        UniqueConstraint("checkout_request_id", name="uq_payments_checkout"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "service_type": self.service_type,
            "amount": float(self.amount) if self.amount else None,
            "payment_method": self.payment_method,
            "status": self.status,
            "reference": self.reference,
            "mpesa_phone": self.mpesa_phone,
            "transaction_id": self.transaction_id,
            "checkout_request_id": self.checkout_request_id,
            "merchant_request_id": self.merchant_request_id,
            "mpesa_receipt": self.mpesa_receipt,
            "mpesa_result_code": self.mpesa_result_code,
            "mpesa_result_desc": self.mpesa_result_desc,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# ─── VALUATION ─────────────────────────────────────────────────

class Valuation(Base, TimestampMixin):
    __tablename__ = "valuations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    service_request_id = Column(UUID(as_uuid=True), ForeignKey("service_requests.id", ondelete="SET NULL"))
    
    # Valuation Details
    valuation_id = Column(String(50), unique=True, index=True)
    valuation_type = Column(String(20), default="standard")  # instant, standard, premium
    
    # Values
    market_value = Column(Numeric(12, 2))
    trade_in_value = Column(Numeric(12, 2))
    private_sale_value = Column(Numeric(12, 2))
    retail_value = Column(Numeric(12, 2))
    auction_value = Column(Numeric(12, 2))
    insurance_value = Column(Numeric(12, 2))
    forced_sale_value = Column(Numeric(12, 2))
    
    # Scores
    confidence_score = Column(Integer)
    risk_score = Column(Integer)
    condition_score = Column(Float)
    
    # Valuation Data
    purpose = Column(String(100))
    region = Column(String(50))
    methodology = Column(String(50))
    comparables = Column(JSON)
    factors = Column(JSON)
    inspection_data = Column(JSON)
    inspector = Column(JSON)
    ai_analysis = Column(JSON)
    market_data = Column(JSON)
    depreciation_data = Column(JSON)
    
    # Status
    status = Column(String(20), default="draft")
    is_verified = Column(Boolean, default=False, server_default=expression.false())
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="valuations")
    user = relationship("UserProfile", back_populates="valuations")
    service_request = relationship("ServiceRequest")
    verifier = relationship("UserProfile", foreign_keys=[verified_by])

    __table_args__ = (
        Index("idx_valuations_vehicle_id", "vehicle_id"),
        Index("idx_valuations_user_id", "user_id"),
        Index("idx_valuations_valuation_id", "valuation_id"),
        Index("idx_valuations_status", "status"),
        Index("idx_valuations_purpose", "purpose"),
        Index("idx_valuations_created_at", "created_at"),
        Index("idx_valuations_comparables", "comparables", postgresql_using="gin"),
        Index("idx_valuations_factors", "factors", postgresql_using="gin"),
        Index("idx_valuations_inspection_data", "inspection_data", postgresql_using="gin"),
        Index("idx_valuations_ai_analysis", "ai_analysis", postgresql_using="gin"),
        Index("idx_valuations_market_data", "market_data", postgresql_using="gin"),
        Index("idx_valuations_depreciation_data", "depreciation_data", postgresql_using="gin"),
        UniqueConstraint("valuation_id", name="uq_valuations_valuation_id"),
    )


# ─── INSPECTION ────────────────────────────────────────────────

class Inspection(Base, TimestampMixin):
    __tablename__ = "inspections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    inspector_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"))
    service_request_id = Column(UUID(as_uuid=True), ForeignKey("service_requests.id", ondelete="SET NULL"))
    
    # Inspection Details
    inspection_type = Column(String(20))
    inspection_date = Column(Date, nullable=False)
    inspection_location = Column(String(255))
    
    # Scores (1-10)
    engine_score = Column(Integer)
    transmission_score = Column(Integer)
    suspension_score = Column(Integer)
    brake_score = Column(Integer)
    paint_score = Column(Integer)
    interior_score = Column(Integer)
    electronics_score = Column(Integer)
    chassis_score = Column(Integer)
    tyre_depth = Column(Float)
    
    # History
    accident_history = Column(String(20))
    service_history = Column(String(20))
    
    # Inspector
    inspector_name = Column(String(255))
    inspector_license = Column(String(50))
    inspector_signature = Column(String(255))
    
    # Findings
    notes = Column(Text)
    images = Column(JSON)
    findings = Column(JSON)
    damage_assessment = Column(JSON)
    repair_estimates = Column(JSON)
    
    # Status
    status = Column(String(20), default="pending")
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="inspections")
    inspector = relationship("UserProfile", back_populates="inspections")
    service_request = relationship("ServiceRequest")

    __table_args__ = (
        CheckConstraint(f"inspection_type IN ('{InspectionType.STANDARD.value}', '{InspectionType.PREMIUM.value}', '{InspectionType.EXPRESS.value}', '{InspectionType.AI.value}', '{InspectionType.VIRTUAL.value}')", name="check_inspection_type"),
        CheckConstraint(f"accident_history IN ('{AccidentHistory.NONE.value}', '{AccidentHistory.MINOR.value}', '{AccidentHistory.MODERATE.value}', '{AccidentHistory.MAJOR.value}', '{AccidentHistory.WRITE_OFF.value}')", name="check_accident_history"),
        Index("idx_inspections_vehicle_id", "vehicle_id"),
        Index("idx_inspections_inspector_id", "inspector_id"),
        Index("idx_inspections_status", "status"),
        Index("idx_inspections_inspection_date", "inspection_date"),
        Index("idx_inspections_created_at", "created_at"),
        Index("idx_inspections_findings", "findings", postgresql_using="gin"),
        Index("idx_inspections_images", "images", postgresql_using="gin"),
        Index("idx_inspections_damage_assessment", "damage_assessment", postgresql_using="gin"),
        Index("idx_inspections_repair_estimates", "repair_estimates", postgresql_using="gin"),
    )


# ─── MILEAGE CLAIM ─────────────────────────────────────────────

class MileageClaim(Base, TimestampMixin):
    __tablename__ = "mileage_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"))
    service_request_id = Column(UUID(as_uuid=True), ForeignKey("service_requests.id", ondelete="SET NULL"))
    
    # Trip Details
    trip_date = Column(Date, nullable=False)
    start_location = Column(String(255))
    end_location = Column(String(255))
    distance_km = Column(Numeric(8, 2))
    vehicle_category = Column(String(50))
    rate_per_km = Column(Numeric(8, 2))
    claim_amount = Column(Numeric(10, 2))
    purpose = Column(String(100))
    notes = Column(Text)
    
    # Supporting Documents
    route_image = Column(String(500))
    odometer_start = Column(BigInteger)
    odometer_end = Column(BigInteger)
    trip_duration = Column(Integer)  # in minutes
    
    # Status
    status = Column(String(20), default="pending")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    approved_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("UserProfile", back_populates="mileage_claims")
    vehicle = relationship("Vehicle", back_populates="mileage_claims")
    approver = relationship("UserProfile", foreign_keys=[approved_by])
    service_request = relationship("ServiceRequest")

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected', 'paid', 'cancelled')", name="check_status"),
        Index("idx_mileage_claims_user_id", "user_id"),
        Index("idx_mileage_claims_vehicle_id", "vehicle_id"),
        Index("idx_mileage_claims_status", "status"),
        Index("idx_mileage_claims_trip_date", "trip_date"),
        Index("idx_mileage_claims_created_at", "created_at"),
    )


# ─── MILEAGE RATE ──────────────────────────────────────────────

class MileageRate(Base, TimestampMixin):
    __tablename__ = "mileage_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_category = Column(String(50), nullable=False)
    rate_per_km = Column(Numeric(8, 2), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    is_active = Column(Boolean, default=True, server_default=expression.true())
    description = Column(String(255))
    
    # Additional rates
    base_rate = Column(Numeric(8, 2))
    fuel_surcharge = Column(Numeric(8, 2))
    maintenance_factor = Column(Numeric(8, 2))
    
    # Metadata
    source = Column(String(50))  # government, corporate, custom
    approved_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    __table_args__ = (
        Index("idx_mileage_rates_active", "is_active"),
        Index("idx_mileage_rates_effective", "effective_from", "effective_to"),
        Index("idx_mileage_rates_category", "vehicle_category"),
        CheckConstraint("rate_per_km > 0", name="check_rate_positive"),
        CheckConstraint("effective_from <= effective_to OR effective_to IS NULL", name="check_effective_dates"),
    )


# ─── VIN SCAN ──────────────────────────────────────────────────

class VINScan(Base, TimestampMixin):
    __tablename__ = "vin_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"))
    
    vin = Column(String(17), nullable=False, index=True)
    image_url = Column(String(500))
    extracted_from = Column(String(100))  # Image URL or text
    confidence = Column(Float)
    model_used = Column(String(50))
    
    # Results
    validation_result = Column(JSON)
    vehicle_data = Column(JSON)
    status = Column(String(20), default="pending")  # pending, verified, failed
    
    # Metadata
    scan_method = Column(String(20))  # ocr, manual, vision
    
    # Relationships
    user = relationship("UserProfile", back_populates="vin_scans")
    vehicle = relationship("Vehicle", back_populates="vin_scans")

    __table_args__ = (
        Index("idx_vin_scans_vin", "vin"),
        Index("idx_vin_scans_user_id", "user_id"),
        Index("idx_vin_scans_vehicle_id", "vehicle_id"),
        Index("idx_vin_scans_status", "status"),
        Index("idx_vin_scans_created_at", "created_at"),
        Index("idx_vin_scans_validation_result", "validation_result", postgresql_using="gin"),
        Index("idx_vin_scans_vehicle_data", "vehicle_data", postgresql_using="gin"),
    )


# ─── FLEET ──────────────────────────────────────────────────────

class Fleet(Base, TimestampMixin):
    __tablename__ = "fleets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    fleet_code = Column(String(50), unique=True, index=True)
    fleet_type = Column(String(50))
    
    # Statistics
    total_vehicles = Column(Integer, default=0)
    active_vehicles = Column(Integer, default=0)
    total_drivers = Column(Integer, default=0)
    active_drivers = Column(Integer, default=0)
    total_annual_km = Column(BigInteger, default=0)
    
    # Financial
    total_annual_cost = Column(Numeric(15, 2), default=0)
    total_fixed_cost = Column(Numeric(15, 2), default=0)
    total_operating_cost = Column(Numeric(15, 2), default=0)
    average_cost_per_km = Column(Numeric(10, 4), default=0)
    
    # Status
    is_active = Column(Boolean, default=True, server_default=expression.true())
    
    # Relationships
    owner = relationship("UserProfile", back_populates="fleets")
    fleet_vehicles = relationship("FleetVehicle", back_populates="fleet", cascade="all, delete-orphan")
    fleet_drivers = relationship("FleetDriver", back_populates="fleet", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_fleets_owner_id", "owner_id"),
        Index("idx_fleets_fleet_code", "fleet_code"),
        Index("idx_fleets_is_active", "is_active"),
        Index("idx_fleets_created_at", "created_at"),
    )


# ─── FLEET VEHICLE ─────────────────────────────────────────────

class FleetVehicle(Base, TimestampMixin):
    __tablename__ = "fleet_vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id = Column(UUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    
    # Assignment
    assignment_status = Column(String(20), default="active")
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    
    # Fleet Specific
    fleet_registration = Column(String(50))
    fleet_number = Column(String(50))
    current_mileage = Column(BigInteger)
    last_service_date = Column(Date)
    next_service_due = Column(Date)
    service_interval_km = Column(Integer)
    
    # Relationships
    fleet = relationship("Fleet", back_populates="fleet_vehicles")
    vehicle = relationship("Vehicle", back_populates="fleet_vehicles")

    __table_args__ = (
        Index("idx_fleet_vehicles_fleet_id", "fleet_id"),
        Index("idx_fleet_vehicles_vehicle_id", "vehicle_id"),
        Index("idx_fleet_vehicles_assignment_status", "assignment_status"),
        UniqueConstraint("fleet_id", "vehicle_id", name="uq_fleet_vehicles"),
    )


# ─── FLEET DRIVER ──────────────────────────────────────────────

class FleetDriver(Base, TimestampMixin):
    __tablename__ = "fleet_drivers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id = Column(UUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"))
    
    # Driver Details
    driver_code = Column(String(50), unique=True, index=True)
    license_number = Column(String(50))
    license_class = Column(String(20))
    license_expiry = Column(Date)
    
    # Employment
    employment_date = Column(Date)
    employment_status = Column(String(20), default="active")
    driver_type = Column(String(20))  # full-time, part-time, contract
    
    # Statistics
    total_trips = Column(Integer, default=0)
    total_km = Column(BigInteger, default=0)
    safety_score = Column(Float)
    rating = Column(Float)
    
    # Relationships
    fleet = relationship("Fleet", back_populates="fleet_drivers")
    user = relationship("UserProfile")

    __table_args__ = (
        Index("idx_fleet_drivers_fleet_id", "fleet_id"),
        Index("idx_fleet_drivers_driver_code", "driver_code"),
        Index("idx_fleet_drivers_employment_status", "employment_status"),
        Index("idx_fleet_drivers_user_id", "user_id"),
    )


# ─── CERTIFICATE ────────────────────────────────────────────────

class Certificate(Base, TimestampMixin):
    __tablename__ = "certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    service_request_id = Column(UUID(as_uuid=True), ForeignKey("service_requests.id", ondelete="SET NULL"))
    
    certificate_number = Column(String(50), unique=True, index=True)
    certificate_type = Column(String(50))  # valuation, inspection, assessment
    
    # Vehicle Details
    vehicle_make = Column(String(100))
    vehicle_model = Column(String(100))
    vehicle_reg = Column(String(20))
    vin = Column(String(17))
    
    # Certificate Data
    result = Column(JSON)
    # FIX: was named `metadata`, which collides with SQLAlchemy's
    # reserved Base.metadata attribute and crashes at import time
    # with "Attribute name 'metadata' is reserved when using the
    # Declarative API." Python attribute renamed to
    # `certificate_metadata`; DB column name kept as "metadata" via
    # the explicit Column("metadata", ...) argument, so no migration
    # is needed if a `metadata` column already exists in the DB.
    certificate_metadata = Column("metadata", JSON)
    pdf_url = Column(String(500))
    qr_code = Column(String(500))
    
    # Status
    status = Column(String(20), default="active")  # active, expired, revoked
    issued_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expiry_date = Column(Date)
    
    # Relationships
    user = relationship("UserProfile", back_populates="certificates")
    service_request = relationship("ServiceRequest", back_populates="certificates")

    __table_args__ = (
        Index("idx_certificates_user_id", "user_id"),
        Index("idx_certificates_certificate_number", "certificate_number"),
        Index("idx_certificates_status", "status"),
        Index("idx_certificates_issued_at", "issued_at"),
        Index("idx_certificates_result", "result", postgresql_using="gin"),
        Index("idx_certificates_metadata", "metadata", postgresql_using="gin"),
        UniqueConstraint("certificate_number", name="uq_certificates_number"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "service_request_id": str(self.service_request_id) if self.service_request_id else None,
            "certificate_number": self.certificate_number,
            "certificate_type": self.certificate_type,
            "vehicle_make": self.vehicle_make,
            "vehicle_model": self.vehicle_model,
            "vehicle_reg": self.vehicle_reg,
            "vin": self.vin,
            "result": self.result,
            "metadata": self.certificate_metadata,
            "pdf_url": self.pdf_url,
            "qr_code": self.qr_code,
            "status": self.status,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
        }


# ─── SYSTEM SETTING ────────────────────────────────────────────

class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=False)
    description = Column(Text)
    is_public = Column(Boolean, default=False, server_default=expression.false())
    category = Column(String(50))
    data_type = Column(String(20))  # string, integer, boolean, json

    __table_args__ = (
        Index("idx_system_settings_key", "setting_key"),
        Index("idx_system_settings_is_public", "is_public"),
        Index("idx_system_settings_category", "category"),
        UniqueConstraint("setting_key", name="uq_system_settings_key"),
    )


# ─── AUDIT LOG ─────────────────────────────────────────────────

class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"))
    
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    resource_data = Column(JSON)
    changes = Column(JSON)
    
    # Request Context
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    request_id = Column(String(50))
    
    # Result
    status = Column(String(20))  # success, failure
    error_message = Column(Text)
    
    # Relationships
    user = relationship("UserProfile", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_resource_type", "resource_type"),
        Index("idx_audit_logs_created_at", "created_at"),
        Index("idx_audit_logs_resource_data", "resource_data", postgresql_using="gin"),
        Index("idx_audit_logs_changes", "changes", postgresql_using="gin"),
        Index("idx_audit_logs_request_id", "request_id"),
    )


# ─── NOTIFICATION ──────────────────────────────────────────────

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    
    type = Column(String(50), nullable=False)  # email, sms, push, in_app
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON)
    
    is_read = Column(Boolean, default=False, server_default=expression.false())
    read_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("UserProfile", back_populates="notifications")

    __table_args__ = (
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_is_read", "is_read"),
        Index("idx_notifications_type", "type"),
        Index("idx_notifications_created_at", "created_at"),
    )


# ─── EXPORT ALL MODELS ─────────────────────────────────────────

__all__ = [
    # Base
    'Base',
    'metadata',
    
    # Enums
    'UserRole',
    'ServiceType',
    'CustomerType',
    'PaymentStatus',
    'ServiceStatus',
    'VehicleCondition',
    'AccidentHistory',
    'TransmissionType',
    'FuelType',
    'InspectionType',
    'PaymentMethod',
    'DocumentVerificationStatus',
    'VehicleType',
    
    # Models
    'UserProfile',
    'Vehicle',
    'VehicleImage',
    'ServiceRequest',
    'Payment',
    'Valuation',
    'Inspection',
    'MileageClaim',
    'MileageRate',
    'VINScan',
    'Fleet',
    'FleetVehicle',
    'FleetDriver',
    'Certificate',
    'SystemSetting',
    'AuditLog',
    'Notification',
]
