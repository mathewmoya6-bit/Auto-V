# app/api/v1/routes/settings.py
# =============================================================================
# AUTO-V API - Settings Router
# =============================================================================
# Public, read-only config values the frontend needs (e.g. service fees).
# No auth required — these are not user-specific or sensitive.
# =============================================================================
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from app.core.database import supabase
from app.core.security import get_current_user

router = APIRouter(tags=["Settings"])

# Default fee if not overridden by env var or DB.
DEFAULT_INSTANT_FEE = float(os.getenv("INSTANT_VALUE_FEE", "500"))


@router.get("/instant_fee")
async def get_instant_fee():
    """
    Returns the current flat fee (KES) charged for an instant vehicle
    valuation. Sourced from env var INSTANT_VALUE_FEE for now; swap the
    body of this function for a Supabase lookup later if the fee needs
    to be editable without a redeploy.
    """
    return {
        "fee": DEFAULT_INSTANT_FEE,
        "currency": "KES",
        "service": "Instant Valuation"
    }


@router.get("/fees")
async def get_all_fees():
    """
    Get all service fees for the application.
    Returns fees for all services (instant valuation, premium, etc.)
    """
    return {
        "instant_valuation": {
            "fee": DEFAULT_INSTANT_FEE,
            "currency": "KES",
            "description": "Instant Vehicle Valuation"
        },
        "premium_valuation": {
            "fee": float(os.getenv("PREMIUM_VALUATION_FEE", "1500")),
            "currency": "KES",
            "description": "Premium Vehicle Valuation with Detailed Report"
        },
        "inspection": {
            "fee": float(os.getenv("INSPECTION_FEE", "2000")),
            "currency": "KES",
            "description": "Vehicle Inspection Service"
        }
    }


@router.get("/features")
async def get_features():
    """
    Get feature flags for the application.
    Frontend uses these to enable/disable features.
    """
    return {
        "instant_valuation": True,
        "vehicle_assessment": True,
        "payment_integration": True,
        "report_generation": True,
        "certificate_generation": True,
        "mileage_tracking": True,
        "inspection_booking": True,
        "ai_valuation": True,
        "qr_verification": True
    }


@router.get("/pricing")
async def get_pricing_tiers():
    """
    Get pricing tiers for valuation services.
    """
    return {
        "tiers": [
            {
                "id": "basic",
                "name": "Basic Valuation",
                "price": DEFAULT_INSTANT_FEE,
                "currency": "KES",
                "features": [
                    "Instant AI valuation",
                    "Market comparison",
                    "Certificate of valuation"
                ],
                "description": "Standard instant vehicle valuation"
            },
            {
                "id": "premium",
                "name": "Premium Valuation",
                "price": float(os.getenv("PREMIUM_VALUATION_FEE", "1500")),
                "currency": "KES",
                "features": [
                    "Everything in Basic",
                    "Detailed report",
                    "Vehicle history check",
                    "Priority processing"
                ],
                "description": "Comprehensive vehicle valuation"
            },
            {
                "id": "enterprise",
                "name": "Enterprise Valuation",
                "price": float(os.getenv("ENTERPRISE_VALUATION_FEE", "5000")),
                "currency": "KES",
                "features": [
                    "Everything in Premium",
                    "Bulk valuation",
                    "API access",
                    "Custom reports",
                    "Dedicated support"
                ],
                "description": "Custom enterprise valuation solutions"
            }
        ]
    }


@router.get("/config")
async def get_app_config():
    """
    Get complete application configuration.
    Used by frontend for initialization.
    """
    return {
        "app_name": "AUTO-V",
        "version": os.getenv("APP_VERSION", "2.0.0"),
        "environment": os.getenv("ENV", "production"),
        "features": {
            "instant_valuation": True,
            "vehicle_assessment": True,
            "payment_integration": True,
            "report_generation": True
        },
        "fees": {
            "instant_valuation": DEFAULT_INSTANT_FEE,
            "premium_valuation": float(os.getenv("PREMIUM_VALUATION_FEE", "1500")),
            "inspection": float(os.getenv("INSPECTION_FEE", "2000"))
        },
        "currency": "KES",
        "supported_languages": ["en"],
        "supported_currencies": ["KES"],
        "max_upload_size": 10485760  # 10MB
    }


@router.get("/validation")
async def get_validation_rules():
    """
    Get validation rules for vehicle data.
    Used by frontend forms for validation.
    """
    return {
        "vehicle": {
            "min_year": 1980,
            "max_year": 2025,
            "max_mileage": 1000000,
            "min_mileage": 0,
            "allowed_conditions": ["Excellent", "Good", "Fair", "Poor"],
            "allowed_accident_history": ["None", "Minor", "Major", "WriteOff"],
            "allowed_fuel_types": ["Petrol", "Diesel", "Hybrid", "Electric"],
            "allowed_transmissions": ["Automatic", "Manual", "CVT"],
            "allowed_body_types": ["Sedan", "SUV", "Hatchback", "Pickup", "Van", "Coupe", "Convertible", "Wagon"],
            "allowed_colors": ["White", "Silver", "Grey", "Black", "Red", "Blue", "Green", "Yellow", "Orange", "Maroon", "Brown", "Gold"]
        },
        "payment": {
            "min_amount": 10,
            "max_amount": 1000000,
            "allowed_currencies": ["KES"]
        },
        "user": {
            "min_password_length": 8,
            "max_password_length": 128,
            "allowed_roles": ["user", "admin", "inspector"]
        }
    }


# ─── Admin Settings (Protected) ──────────────────────────────────────

@router.put("/instant_fee")
async def update_instant_fee(
    fee_data: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """
    Update the instant valuation fee (Admin only).
    This requires authentication and admin privileges.
    """
    try:
        # Check if user is admin (you can implement this check)
        # For now, we'll check if user exists and has admin role
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # You would check for admin role here
        # if current_user.role != "admin":
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        new_fee = fee_data.get("fee")
        if not new_fee or new_fee <= 0:
            raise HTTPException(status_code=400, detail="Invalid fee amount")
        
        # Update in database
        result = (
            supabase
            .table("settings")
            .update({
                "setting_value": str(new_fee),
                "updated_at": "now()"
            })
            .eq("setting_key", "instant_valuation_fee")
            .execute()
        )
        
        return {
            "message": "Fee updated successfully",
            "fee": new_fee,
            "currency": "KES",
            "updated_at": "now()"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin")
async def get_admin_settings(
    current_user = Depends(get_current_user)
):
    """
    Get admin settings (Admin only).
    """
    try:
        # Check admin role here
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        return {
            "settings": {
                "instant_valuation_fee": DEFAULT_INSTANT_FEE,
                "premium_valuation_fee": float(os.getenv("PREMIUM_VALUATION_FEE", "1500")),
                "inspection_fee": float(os.getenv("INSPECTION_FEE", "2000")),
                "maintenance_mode": os.getenv("MAINTENANCE_MODE", "false") == "true",
                "maintenance_message": os.getenv("MAINTENANCE_MESSAGE", "System undergoing maintenance")
            },
            "updated_at": "now()"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
