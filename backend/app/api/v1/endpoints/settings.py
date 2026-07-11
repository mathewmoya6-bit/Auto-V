from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
from datetime import datetime
from app.core.database import supabase, admin
from app.core.security import get_current_active_user

router = APIRouter()

# Single source of truth for the un-configured-state default. Used only
# when no "instant_valuation_fee" row exists yet in the settings table —
# a genuine "not configured" state, not a stand-in for a failed query.
DEFAULT_INSTANT_FEE = 500
DEFAULT_CURRENCY = "KES"


@router.get("/settings/instant_fee")
async def get_instant_fee(
    current_user = Depends(get_current_active_user)
):
    """
    Get the current service fee for instant valuation
    """
    try:
        result = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "instant_valuation_fee")
            .execute()
        )
    except Exception as e:
        # A real query failure — don't mask it as a successful default.
        # The frontend needs to know this fetch actually failed.
        raise HTTPException(status_code=500, detail=f"Failed to fetch instant fee: {e}")

    if result.data:
        setting = result.data[0]
        return {
            "fee": int(setting.get("setting_value", DEFAULT_INSTANT_FEE)),
            "currency": setting.get("currency", DEFAULT_CURRENCY),
            "description": setting.get("description", "Instant Vehicle Valuation Service Fee"),
            "updated_at": setting.get("updated_at")
        }

    # No row yet — genuinely not configured. This IS a legitimate default,
    # not an error being papered over.
    return {
        "fee": DEFAULT_INSTANT_FEE,
        "currency": DEFAULT_CURRENCY,
        "description": "Instant Vehicle Valuation Service Fee",
        "updated_at": None
    }


@router.put("/settings/instant_fee")
async def update_instant_fee(
    fee_data: Dict[str, Any],
    current_user = Depends(get_current_active_user)
):
    """
    Update the service fee for instant valuation (Admin only)
    """
    # TODO: add an actual admin-role check here, not just "any authenticated user"
    if "fee" not in fee_data:
        raise HTTPException(status_code=400, detail="'fee' is required")
    try:
        fee = int(fee_data["fee"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="'fee' must be a number")

    currency = fee_data.get("currency", DEFAULT_CURRENCY)
    description = fee_data.get("description", "Instant Vehicle Valuation Service Fee")

    try:
        # Check if setting exists
        existing = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "instant_valuation_fee")
            .execute()
        )
        
        if existing.data:
            # Update existing
            result = (
                admin
                .table("settings")
                .update({
                    "setting_value": str(fee),
                    "currency": currency,
                    "description": description,
                    "updated_at": datetime.now().isoformat()
                })
                .eq("setting_key", "instant_valuation_fee")
                .execute()
            )
        else:
            # Insert new
            result = (
                admin
                .table("settings")
                .insert({
                    "setting_key": "instant_valuation_fee",
                    "setting_value": str(fee),
                    "currency": currency,
                    "description": description,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                })
                .execute()
            )
        
        return {
            "message": "Service fee updated successfully",
            "fee": fee,
            "currency": currency,
            "description": description
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


DEFAULT_FEATURES = {
    "instant_valuation": True,
    "payment_integration": True,
    "ai_valuation": True,
    "report_generation": True,
    "vehicle_tracking": True,
    "certificate_generation": True
}


@router.get("/settings/features")
async def get_features(
    current_user = Depends(get_current_active_user)
):
    """
    Get all feature flags for the application
    """
    try:
        result = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "features")
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch features: {e}")

    if result.data:
        setting = result.data[0]
        try:
            import json
            features = json.loads(setting.get("setting_value", "{}"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=500, detail="Stored 'features' setting is not valid JSON")

        return {
            "features": features,
            "updated_at": setting.get("updated_at")
        }

    # Not yet configured — legitimate default, not an error being hidden.
    return {
        "features": DEFAULT_FEATURES,
        "updated_at": None
    }


DEFAULT_VALIDATION_RULES = {
    "min_year": 1980,
    "max_year": 2025,
    "max_mileage": 1000000,
    "min_mileage": 0,
    "allowed_conditions": ["Excellent", "Good", "Fair", "Poor"],
    "allowed_accident_history": ["None", "Minor", "Major", "WriteOff"],
    "allowed_fuel_types": ["Petrol", "Diesel", "Hybrid", "Electric"],
    "allowed_transmissions": ["Automatic", "Manual", "CVT"]
}


@router.get("/settings/validation")
async def get_validation_rules(
    current_user = Depends(get_current_active_user)
):
    """
    Get validation rules for vehicle valuation
    """
    try:
        result = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "validation_rules")
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch validation rules: {e}")

    if result.data:
        setting = result.data[0]
        try:
            import json
            rules = json.loads(setting.get("setting_value", "{}"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=500, detail="Stored 'validation_rules' setting is not valid JSON")

        return {
            "rules": rules,
            "updated_at": setting.get("updated_at")
        }

    # Not yet configured — legitimate default.
    return {
        "rules": DEFAULT_VALIDATION_RULES,
        "updated_at": None
    }


DEFAULT_VALUATION_FACTORS = {
    "base_values": {
        "Car": 2000000,
        "Bike": 300000,
        "Tricycle": 200000
    },
    "depreciation_rate": 0.12,
    "condition_factors": {
        "Excellent": 1.2,
        "Good": 1.0,
        "Fair": 0.8,
        "Poor": 0.6
    },
    "accident_factors": {
        "None": 1.0,
        "Minor": 0.85,
        "Major": 0.6,
        "WriteOff": 0.3
    },
    "location_factors": {
        "Nairobi": 1.1,
        "Mombasa": 1.05,
        "Kisumu": 0.95,
        "Nakuru": 0.98,
        "Eldoret": 0.95,
        "Kiambu": 1.08,
        "Kajiado": 1.05,
        "Machakos": 1.02,
        "Other": 0.9
    },
    "previous_owners_factor": 0.03,
    "mileage_factor": {
        "max_reduction": 0.7,
        "max_mileage": 200000
    },
    "random_factor_range": 0.1
}


@router.get("/settings/valuation_factors")
async def get_valuation_factors(
    current_user = Depends(get_current_active_user)
):
    """
    Get valuation factors used in AI calculation
    """
    try:
        result = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "valuation_factors")
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch valuation factors: {e}")

    if result.data:
        setting = result.data[0]
        try:
            import json
            factors = json.loads(setting.get("setting_value", "{}"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=500, detail="Stored 'valuation_factors' setting is not valid JSON")

        return {
            "factors": factors,
            "updated_at": setting.get("updated_at")
        }

    # Not yet configured — legitimate default.
    return {
        "factors": DEFAULT_VALUATION_FACTORS,
        "updated_at": None
    }


DEFAULT_PRICING_TIERS = {
    "basic": {
        "name": "Basic Valuation",
        "price": DEFAULT_INSTANT_FEE,
        "currency": DEFAULT_CURRENCY,
        "features": [
            "Instant AI valuation",
            "Market comparison",
            "Certificate of valuation"
        ],
        "description": "Standard instant vehicle valuation"
    },
    "premium": {
        "name": "Premium Valuation",
        "price": 1500,
        "currency": DEFAULT_CURRENCY,
        "features": [
            "Instant AI valuation",
            "Market comparison",
            "Certificate of valuation",
            "Detailed report",
            "Vehicle history check",
            "Priority processing"
        ],
        "description": "Comprehensive vehicle valuation with detailed report"
    },
    "enterprise": {
        "name": "Enterprise Valuation",
        "price": 5000,
        "currency": DEFAULT_CURRENCY,
        "features": [
            "Everything in Premium",
            "Bulk valuation",
            "API access",
            "Custom reports",
            "Dedicated support",
            "White-label certificates"
        ],
        "description": "Custom enterprise valuation solutions"
    }
}


@router.get("/settings/pricing")
async def get_pricing_tiers(
    current_user = Depends(get_current_active_user)
):
    """
    Get pricing tiers for valuation services
    """
    try:
        result = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "pricing_tiers")
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pricing tiers: {e}")

    if result.data:
        setting = result.data[0]
        try:
            import json
            tiers = json.loads(setting.get("setting_value", "{}"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=500, detail="Stored 'pricing_tiers' setting is not valid JSON")

        return {
            "tiers": tiers,
            "updated_at": setting.get("updated_at")
        }

    # Not yet configured — legitimate default.
    return {
        "tiers": DEFAULT_PRICING_TIERS,
        "updated_at": None
    }
