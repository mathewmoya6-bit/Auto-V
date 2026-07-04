"""
Fuel Price Service - EPRA Integration
Production-ready fuel price management with Supabase as single source of truth
"""

import os
import re
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from supabase import create_client, Client

from app.core.config import settings
from app.core.database import supabase
from app.core.dependencies import get_current_user, get_current_user_optional
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fuel", tags=["Fuel"])


# ─── Constants ──────────────────────────────────────────────────

# EPRA Default Prices (14th of each month)
EPRA_DEFAULTS = {
    "petrol": 214.03,
    "diesel": 222.86,
    "hybrid": 214.03,  # Hybrid vehicles use petrol
    "lpg": 120.00,
    "electric": 20.00,
    "kerosene": 163.00
}

EPRA_URL = "https://www.epra.go.ke/petroleum-prices/"


# ─── Pydantic Models ──────────────────────────────────────────

class FuelPrices(BaseModel):
    """Fuel prices model"""
    petrol: float = Field(..., description="Petrol price per litre (KES)")
    diesel: float = Field(..., description="Diesel price per litre (KES)")
    hybrid: float = Field(..., description="Hybrid fuel price per litre (KES)")
    lpg: Optional[float] = Field(None, description="LPG price per kg (KES)")
    electric: Optional[float] = Field(None, description="Electricity price per kWh (KES)")
    kerosene: Optional[float] = Field(None, description="Kerosene price per litre (KES)")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    source: Optional[str] = Field("epra", description="Data source")


class FuelPriceResponse(BaseModel):
    """Fuel price response model"""
    success: bool
    data: Optional[FuelPrices] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


class FuelPriceUpdateResponse(BaseModel):
    """Fuel price update response model"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ─── Helper Functions ──────────────────────────────────────────

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now(timezone.utc).isoformat()


def get_epra_defaults() -> Dict[str, float]:
    """Get EPRA default prices."""
    return EPRA_DEFAULTS.copy()


def fetch_epra_prices() -> Dict[str, float]:
    """
    Fetch current fuel prices from EPRA website.
    
    Returns:
        Dict with fuel prices or EPRA defaults if fetch fails
    """
    try:
        response = requests.get(
            EPRA_URL,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
        )

        if response.status_code == 200:
            html = response.text.lower()
            
            # Search for petrol and diesel prices
            petrol_match = re.search(r'petrol[^0-9]*(\d+\.?\d*)', html)
            diesel_match = re.search(r'diesel[^0-9]*(\d+\.?\d*)', html)
            kerosene_match = re.search(r'kerosene[^0-9]*(\d+\.?\d*)', html)

            petrol = float(petrol_match.group(1)) if petrol_match else None
            diesel = float(diesel_match.group(1)) if diesel_match else None
            kerosene = float(kerosene_match.group(1)) if kerosene_match else None

            if petrol and diesel:
                return {
                    "petrol": petrol,
                    "diesel": diesel,
                    "hybrid": petrol,  # Hybrid uses petrol
                    "lpg": EPRA_DEFAULTS.get("lpg", 120.00),
                    "electric": EPRA_DEFAULTS.get("electric", 20.00),
                    "kerosene": kerosene or EPRA_DEFAULTS.get("kerosene", 163.00)
                }
                
    except requests.exceptions.Timeout:
        logger.warning("EPRA fetch timed out, using defaults")
    except requests.exceptions.RequestException as e:
        logger.warning(f"EPRA fetch error: {str(e)}")
    except Exception as e:
        logger.error(f"EPRA parse error: {str(e)}")

    # Fallback to EPRA defaults
    return get_epra_defaults()


def save_prices_to_supabase(prices: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """
    Save fuel prices to Supabase.
    
    Args:
        prices: Fuel prices dictionary
        
    Returns:
        Saved record or None
    """
    try:
        # Check if record exists
        existing = supabase.table("fuel_prices").select("id").limit(1).execute()

        data = {
            "petrol": prices.get("petrol"),
            "diesel": prices.get("diesel"),
            "hybrid": prices.get("hybrid"),
            "lpg": prices.get("lpg"),
            "electric": prices.get("electric"),
            "kerosene": prices.get("kerosene"),
            "updated_at": format_timestamp()
        }

        if existing.data and len(existing.data) > 0:
            result = supabase.table("fuel_prices") \
                .update(data) \
                .eq("id", existing.data[0]["id"]) \
                .execute()
        else:
            result = supabase.table("fuel_prices").insert(data).execute()

        return result.data[0] if result.data else None
        
    except Exception as e:
        logger.error(f"Supabase save error: {str(e)}")
        return None


def get_latest_prices_from_supabase() -> Optional[Dict[str, Any]]:
    """Get latest fuel prices from Supabase."""
    try:
        result = supabase.table("fuel_prices") \
            .select("*") \
            .order("updated_at", desc=True) \
            .limit(1) \
            .execute()

        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Supabase fetch error: {str(e)}")
        return None


# ─── Routes ──────────────────────────────────────────────────

@router.get("/prices", response_model=FuelPriceResponse)
@rate_limit(limit=30, per=60)
@log_request
@handle_errors
async def get_fuel_prices():
    """
    Get current fuel prices from Supabase.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Fuel prices
    - `error`: Error message if unsuccessful
    """
    try:
        # Get latest prices from Supabase
        saved = get_latest_prices_from_supabase()

        if saved:
            return FuelPriceResponse(
                success=True,
                data=FuelPrices(
                    petrol=float(saved.get("petrol", EPRA_DEFAULTS["petrol"])),
                    diesel=float(saved.get("diesel", EPRA_DEFAULTS["diesel"])),
                    hybrid=float(saved.get("hybrid", EPRA_DEFAULTS["hybrid"])),
                    lpg=float(saved.get("lpg", EPRA_DEFAULTS["lpg"])),
                    electric=float(saved.get("electric", EPRA_DEFAULTS["electric"])),
                    kerosene=float(saved.get("kerosene", EPRA_DEFAULTS.get("kerosene", 163.00))),
                    last_updated=saved.get("updated_at"),
                    source="supabase"
                ),
                timestamp=format_timestamp()
            )

        # Fallback to defaults
        return FuelPriceResponse(
            success=True,
            data=FuelPrices(
                **EPRA_DEFAULTS,
                last_updated=format_timestamp(),
                source="epra_defaults"
            ),
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get fuel prices error: {str(e)}", exc_info=True)
        return FuelPriceResponse(
            success=False,
            error=str(e)
        )


@router.post("/prices/update", response_model=FuelPriceUpdateResponse)
@rate_limit(limit=5, per=60)
@require_role("admin")
@log_request
@handle_errors
async def update_fuel_prices(
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch EPRA prices and save to Supabase.
    
    **Response:**
    - `success`: Boolean indicating success
    - `message`: Status message
    - `data`: Updated prices
    - `error`: Error message if unsuccessful
    """
    try:
        # Fetch EPRA prices
        prices = fetch_epra_prices()
        
        # Save to Supabase
        saved = save_prices_to_supabase(prices)

        if saved:
            return FuelPriceUpdateResponse(
                success=True,
                message="Fuel prices updated successfully",
                data=prices
            )
        else:
            return FuelPriceUpdateResponse(
                success=False,
                error="Failed to save prices to Supabase"
            )
        
    except Exception as e:
        logger.error(f"Update fuel prices error: {str(e)}", exc_info=True)
        return FuelPriceUpdateResponse(
            success=False,
            error=str(e)
        )


@router.get("/prices/history", response_model=FuelPriceResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_fuel_price_history(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """
    Get fuel price history.
    
    **Query Parameters:**
    - `limit`: Number of records to return (default: 10)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of price records
    - `error`: Error message if unsuccessful
    """
    try:
        result = supabase.table("fuel_prices") \
            .select("*") \
            .order("updated_at", desc=True) \
            .limit(limit) \
            .execute()

        return FuelPriceResponse(
            success=True,
            data={
                "history": result.data,
                "count": len(result.data)
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get fuel price history error: {str(e)}", exc_info=True)
        return FuelPriceResponse(
            success=False,
            error=str(e)
        )


@router.get("/calculate", response_model=FuelPriceResponse)
@rate_limit(limit=30, per=60)
@log_request
@handle_errors
async def calculate_fuel_cost(
    fuel_type: str = Query(..., description="Fuel type (petrol, diesel, hybrid, electric, lpg)"),
    quantity: float = Query(..., description="Quantity in litres or kWh", gt=0),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Calculate fuel cost based on current prices.
    
    **Query Parameters:**
    - `fuel_type`: Fuel type (petrol, diesel, hybrid, electric, lpg)
    - `quantity`: Quantity in litres or kWh
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Cost calculation
    - `error`: Error message if unsuccessful
    """
    try:
        # Get current prices
        prices = get_latest_prices_from_supabase()
        
        if not prices:
            prices = EPRA_DEFAULTS
        
        fuel_type = fuel_type.lower()
        price_per_unit = prices.get(fuel_type)
        
        if price_per_unit is None:
            return FuelPriceResponse(
                success=False,
                error=f"Invalid fuel type: {fuel_type}. Valid types: petrol, diesel, hybrid, electric, lpg"
            )
        
        total_cost = price_per_unit * quantity
        
        return FuelPriceResponse(
            success=True,
            data={
                "fuel_type": fuel_type,
                "quantity": quantity,
                "price_per_unit": price_per_unit,
                "total_cost": round(total_cost, 2),
                "currency": "KES",
                "unit": "litres" if fuel_type != "electric" else "kWh"
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Calculate fuel cost error: {str(e)}", exc_info=True)
        return FuelPriceResponse(
            success=False,
            error=str(e)
        )


@router.get("/vehicles/makes", response_model=FuelPriceResponse)
@rate_limit(limit=30, per=60)
@log_request
@handle_errors
async def get_vehicle_makes():
    """
    Get all vehicle makes.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of vehicle makes
    - `error`: Error message if unsuccessful
    """
    try:
        result = supabase.table("vehicle_makes") \
            .select("*") \
            .order("name") \
            .execute()

        return FuelPriceResponse(
            success=True,
            data=result.data,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get vehicle makes error: {str(e)}", exc_info=True)
        return FuelPriceResponse(
            success=False,
            error=str(e)
        )


@router.get("/vehicles/models", response_model=FuelPriceResponse)
@rate_limit(limit=30, per=60)
@log_request
@handle_errors
async def get_vehicle_models(
    make_id: Optional[int] = Query(None, description="Filter by make ID")
):
    """
    Get vehicle models by make.
    
    **Query Parameters:**
    - `make_id`: Filter by make ID (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of vehicle models
    - `error`: Error message if unsuccessful
    """
    try:
        query = supabase.table("vehicle_models") \
            .select("*") \
            .order("name")
        
        if make_id:
            query = query.eq("make_id", make_id)
        
        result = query.execute()

        return FuelPriceResponse(
            success=True,
            data=result.data,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get vehicle models error: {str(e)}", exc_info=True)
        return FuelPriceResponse(
            success=False,
            error=str(e)
        )


@router.get("/ping", response_model=FuelPriceResponse)
@log_request
@handle_errors
async def ping():
    """
    Health check endpoint.
    
    **Response:**
    - `status`: Service status
    - `timestamp`: Current timestamp
    """
    return FuelPriceResponse(
        success=True,
        data={
            "status": "ok",
            "service": "epra-fuel-server",
            "timestamp": format_timestamp()
        }
    )


@router.get("/", response_model=FuelPriceResponse)
@log_request
@handle_errors
async def index():
    """
    Root endpoint with service information.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Service information
    """
    return FuelPriceResponse(
        success=True,
        data={
            "name": "EPRA Fuel Server",
            "version": "2.0.0",
            "status": "running",
            "endpoints": [
                {"path": "/api/fuel/prices", "method": "GET", "description": "Get current fuel prices"},
                {"path": "/api/fuel/prices/update", "method": "POST", "description": "Fetch EPRA prices"},
                {"path": "/api/fuel/prices/history", "method": "GET", "description": "Get price history"},
                {"path": "/api/fuel/calculate", "method": "GET", "description": "Calculate fuel cost"},
                {"path": "/api/fuel/vehicles/makes", "method": "GET", "description": "Get vehicle makes"},
                {"path": "/api/fuel/vehicles/models", "method": "GET", "description": "Get vehicle models"}
            ],
            "default_prices": EPRA_DEFAULTS
        },
        timestamp=format_timestamp()
    )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
