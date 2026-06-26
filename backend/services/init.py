"""
Services Package
"""

from app.services.supabase_client import (
    # Payments
    create_payment,
    get_payment_by_payment_id,
    get_payment_by_checkout_request_id,
    get_payment_by_merchant_request_id,
    update_payment,
    update_payment_by_checkout_id,
    get_payment_status,
    get_user_payments,
    get_all_payments,
    get_pending_payments,
    delete_payment,
    
    # Vehicles
    create_vehicle,
    get_vehicle_by_vin,
    get_vehicle_by_license_plate,
    get_user_vehicles,
    update_vehicle,
    
    # Valuations
    create_valuation,
    get_valuation_by_id,
    get_valuations_by_user,
    get_valuations_by_vin,
    
    # Certificates
    create_certificate,
    get_certificate_by_number,
    get_user_certificates,
    update_certificate,
    
    # Service Requests
    create_service_request,
    get_service_request_by_id,
    get_user_service_requests,
    update_service_request,
    
    # Users
    get_user_by_id,
    get_user_by_email,
    create_user,
    update_user,
    
    # Test
    test_connection,
    test_payment_flow,
    
    # Compatibility
    get_supabase_client,
)

__all__ = [
    # Payments
    "create_payment",
    "get_payment_by_payment_id",
    "get_payment_by_checkout_request_id",
    "get_payment_by_merchant_request_id",
    "update_payment",
    "update_payment_by_checkout_id",
    "get_payment_status",
    "get_user_payments",
    "get_all_payments",
    "get_pending_payments",
    "delete_payment",
    
    # Vehicles
    "create_vehicle",
    "get_vehicle_by_vin",
    "get_vehicle_by_license_plate",
    "get_user_vehicles",
    "update_vehicle",
    
    # Valuations
    "create_valuation",
    "get_valuation_by_id",
    "get_valuations_by_user",
    "get_valuations_by_vin",
    
    # Certificates
    "create_certificate",
    "get_certificate_by_number",
    "get_user_certificates",
    "update_certificate",
    
    # Service Requests
    "create_service_request",
    "get_service_request_by_id",
    "get_user_service_requests",
    "update_service_request",
    
    # Users
    "get_user_by_id",
    "get_user_by_email",
    "create_user",
    "update_user",
    
    # Test
    "test_connection",
    "test_payment_flow",
    
    # Compatibility
    "get_supabase_client",
]
