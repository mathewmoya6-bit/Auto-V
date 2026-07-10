from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
from datetime import datetime
from app.core.database import supabase, admin
from app.core.security import get_current_active_user

router = APIRouter()


@router.get("/settings/instant_fee")
async def get_instant_fee(
    current_user = Depends(get_current_active_user)
):
    """
    Get the current service fee for instant valuation
    """
    try:
        # Try to get from database first
        result = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "instant_valuation_fee")
            .execute()
        )
        
        if result.data:
            setting = result.data[0]
            return {
                "fee": int(setting.get("setting_value", 500)),
                "currency": setting.get("currency", "KES"),
                "description": setting.get("description", "Instant Vehicle Valuation Service Fee"),
                "updated_at": setting.get("updated_at")
            }
        
        # Fallback to default
        return {
            "fee": 500,
            "currency": "KES",
            "description": "Instant Vehicle Valuation Service Fee",
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        # If table doesn't exist, return default
        return {
            "fee": 500,
            "currency": "KES",
            "description": "Instant Vehicle Valuation Service Fee",
            "updated_at": datetime.now().isoformat()
        }


@router.put("/settings/instant_fee")
async def update_instant_fee(
    fee_data: Dict[str, Any],
    current_user = Depends(get_current_active_user)
):
    """
    Update the service fee for instant valuation (Admin only)
    """
    try:
        # Check if user is admin (you may want to add admin check)
        # For now, we'll allow any authenticated user, but you should add role check
        
        fee = fee_data.get("fee", 500)
        currency = fee_data.get("currency", "KES")
        description = fee_data.get("description", "Instant Vehicle Valuation Service Fee")
        
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


@router.get("/settings/features")
async def get_features(
    current_user = Depends(get_current_active_user)
):
    """
    Get all feature flags for the application
    """
    try:
        # Try to get from database
        result = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "features")
            .execute()
        )
        
        if result.data:
            setting = result.data[0]
            # Parse JSON if stored as string
            try:
                import json
                features = json.loads(setting.get("setting_value", "{}"))
            except:
                features = {}
            
            return {
                "features": features,
                "updated_at": setting.get("updated_at")
            }
        
        # Return default features
        return {
            "features": {
                "instant_valuation": True,
                "payment_integration": True,
                "ai_valuation": True,
                "report_generation": True,
                "vehicle_tracking": True,
                "certificate_generation": True
            },
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        # Return default features if error
        return {
            "features": {
                "instant_valuation": True,
                "payment_integration": True,
                "ai_valuation": True,
                "report_generation": True,
                "vehicle_tracking": True,
                "certificate_generation": True
            },
            "updated_at": datetime.now().isoformat()
        }


@router.get("/settings/validation")
async def get_validation_rules(
    current_user = Depends(get_current_active_user)
):
    """
    Get validation rules for vehicle valuation
    """
    try:
        # Try to get from database
        result = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "validation_rules")
            .execute()
        )
        
        if result.data:
            setting = result.data[0]
            try:
                import json
                rules = json.loads(setting.get("setting_value", "{}"))
            except:
                rules = {}
            
            return {
                "rules": rules,
                "updated_at": setting.get("updated_at")
            }
        
        # Return default validation rules
        return {
            "rules": {
                "min_year": 1980,
                "max_year": 2025,
                "max_mileage": 1000000,
                "min_mileage": 0,
                "allowed_conditions": ["Excellent", "Good", "Fair", "Poor"],
                "allowed_accident_history": ["None", "Minor", "Major", "WriteOff"],
                "allowed_fuel_types": ["Petrol", "Diesel", "Hybrid", "Electric"],
                "allowed_transmissions": ["Automatic", "Manual", "CVT"]
            },
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        # Return default rules if error
        return {
            "rules": {
                "min_year": 1980,
                "max_year": 2025,
                "max_mileage": 1000000,
                "min_mileage": 0,
                "allowed_conditions": ["Excellent", "Good", "Fair", "Poor"],
                "allowed_accident_history": ["None", "Minor", "Major", "WriteOff"],
                "allowed_fuel_types": ["Petrol", "Diesel", "Hybrid", "Electric"],
                "allowed_transmissions": ["Automatic", "Manual", "CVT"]
            },
            "updated_at": datetime.now().isoformat()
        }


@router.get("/settings/valuation_factors")
async def get_valuation_factors(
    current_user = Depends(get_current_active_user)
):
    """
    Get valuation factors used in AI calculation
    """
    try:
        # Try to get from database
        result = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "valuation_factors")
            .execute()
        )
        
        if result.data:
            setting = result.data[0]
            try:
                import json
                factors = json.loads(setting.get("setting_value", "{}"))
            except:
                factors = {}
            
            return {
                "factors": factors,
                "updated_at": setting.get("updated_at")
            }
        
        # Return default valuation factors
        return {
            "factors": {
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
            },
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        # Return default factors if error
        return {
            "factors": {
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
            },
            "updated_at": datetime.now().isoformat()
        }


@router.get("/settings/pricing")
async def get_pricing_tiers(
    current_user = Depends(get_current_active_user)
):
    """
    Get pricing tiers for valuation services
    """
    try:
        # Try to get from database
        result = (
            supabase
            .table("settings")
            .select("*")
            .eq("setting_key", "pricing_tiers")
            .execute()
        )
        
        if result.data:
            setting = result.data[0]
            try:
                import json
                tiers = json.loads(setting.get("setting_value", "{}"))
            except:
                tiers = {}
            
            return {
                "tiers": tiers,
                "updated_at": setting.get("updated_at")
            }
        
        # Return default pricing tiers
        return {
            "tiers": {
                "basic": {
                    "name": "Basic Valuation",
                    "price": 500,
                    "currency": "KES",
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
                    "currency": "KES",
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
                    "currency": "KES",
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
            },
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        # Return default tiers if error
        return {
            "tiers": {
                "basic": {
                    "name": "Basic Valuation",
                    "price": 500,
                    "currency": "KES",
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
                    "currency": "KES",
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
                    "currency": "KES",
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
            },
            "updated_at": datetime.now().isoformat()
        }
