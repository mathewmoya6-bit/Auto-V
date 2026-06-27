"""
Services Package - All Business Logic Services
"""

from app.services.valuation import ValuationService, valuation_service
from app.services.mpesa import MpesaService, mpesa_service
from app.services.ai import AIService, ai_service
from app.services.valuation_engine import ValuationEngine, valuation_engine
from app.services.inspection import InspectionService, inspection_service
from app.services.fleet import FleetService, fleet_service
from app.services.mileage import MileageService, mileage_service
from app.services.report import ReportService, report_service
from app.services.certificate import CertificateService, certificate_service
from app.services.notification import NotificationService, notification_service
from app.services.email import EmailService, email_service
from app.services.vin_validator import vin_validator
from app.services.carapi_service import car_api, get_carapi_service
from app.services.supabase_client import supabase, get_supabase

__all__ = [
    # Valuation
    "ValuationService",
    "valuation_service",
    "ValuationEngine",
    "valuation_engine",
    
    # M-Pesa
    "MpesaService",
    "mpesa_service",
    
    # AI
    "AIService",
    "ai_service",
    
    # Inspection
    "InspectionService",
    "inspection_service",
    
    # Fleet
    "FleetService",
    "fleet_service",
    
    # Mileage
    "MileageService",
    "mileage_service",
    
    # Report
    "ReportService",
    "report_service",
    
    # Certificate
    "CertificateService",
    "certificate_service",
    
    # Notification
    "NotificationService",
    "notification_service",
    
    # Email
    "EmailService",
    "email_service",
    
    # VIN
    "vin_validator",
    
    # CarAPI
    "car_api",
    "get_carapi_service",
    
    # Supabase
    "supabase",
    "get_supabase"
]
