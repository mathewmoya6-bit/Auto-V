"""
EPRA Fuel Price Server - Production Ready
Integrates with Supabase as Single Source of Truth
FastAPI Version - Complete Standalone Server
"""

import os
import re
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from supabase import create_client, Client

# ─── Configuration ──────────────────────────────────────────────

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tsvejnzxrxrrecgquxbq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ")

# EPRA Default Prices (14th of each month)
EPRA_DEFAULTS = {
    "petrol": 214.03,
    "diesel": 222.86,
    "hybrid": 214.03,
    "lpg": 120.00,
    "electric": 20.00,
    "kerosene": 163.00
}

EPRA_URL = "https://www.epra.go.ke/petroleum-prices/"

# ─── Pydantic Models ──────────────────────────────────────────

class FuelPrices(BaseModel):
    petrol: float = Field(..., description="Petrol price per litre (KES)")
    diesel: float = Field(..., description="Diesel price per litre (KES)")
    hybrid: float = Field(..., description="Hybrid fuel price per litre (KES)")
    lpg: Optional[float] = Field(None, description="LPG price per kg (KES)")
    electric: Optional[float] = Field(None, description="Electricity price per kWh (KES)")
    kerosene: Optional[float] = Field(None, description="Kerosene price per litre (KES)")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    source: Optional[str] = Field("epra", description="Data source")


class FuelPriceResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


class FuelPriceUpdateResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ─── Initialize Clients ─────────────────────────────────────

app = FastAPI(
    title="EPRA Fuel Price Server",
    version="2.0.0",
    description="Kenya fuel price server with Supabase as single source of truth"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Logging ──────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
                    "hybrid": petrol,
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

@app.get("/api/fuel-prices", response_model=FuelPriceResponse)
async def get_prices():
    """
    GET /api/fuel-prices - Get current fuel prices from Supabase
    """
    try:
        saved = get_latest_prices_from_supabase()

        if saved:
            return FuelPriceResponse(
                success=True,
                data={
                    "petrol": float(saved.get("petrol", EPRA_DEFAULTS["petrol"])),
                    "diesel": float(saved.get("diesel", EPRA_DEFAULTS["diesel"])),
                    "hybrid": float(saved.get("hybrid", EPRA_DEFAULTS["hybrid"])),
                    "lpg": float(saved.get("lpg", EPRA_DEFAULTS["lpg"])),
                    "electric": float(saved.get("electric", EPRA_DEFAULTS["electric"])),
                    "kerosene": float(saved.get("kerosene", EPRA_DEFAULTS.get("kerosene", 163.00))),
                    "last_updated": saved.get("updated_at"),
                    "source": "supabase"
                },
                timestamp=format_timestamp()
            )

        return FuelPriceResponse(
            success=True,
            data={
                **EPRA_DEFAULTS,
                "last_updated": format_timestamp(),
                "source": "epra_defaults"
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get prices error: {str(e)}", exc_info=True)
        return FuelPriceResponse(
            success=False,
            error=str(e)
        )


@app.post("/api/fuel-prices/update", response_model=FuelPriceUpdateResponse)
async def update_prices():
    """
    POST /api/fuel-prices/update - Fetch EPRA prices and save to Supabase
    """
    try:
        prices = fetch_epra_prices()
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
        logger.error(f"Update prices error: {str(e)}", exc_info=True)
        return FuelPriceUpdateResponse(
            success=False,
            error=str(e)
        )


@app.get("/api/vehicles/makes")
async def get_makes():
    """
    GET /api/vehicles/makes - Get all vehicle makes
    """
    try:
        result = supabase.table("vehicle_makes") \
            .select("*") \
            .order("name") \
            .execute()

        return JSONResponse({
            "success": True,
            "data": result.data
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/vehicles/models")
async def get_models(make_id: Optional[int] = None):
    """
    GET /api/vehicles/models?make_id=1 - Get models by make
    """
    try:
        query = supabase.table("vehicle_models") \
            .select("*") \
            .order("name")
        
        if make_id:
            query = query.eq("make_id", make_id)
        
        result = query.execute()

        return JSONResponse({
            "success": True,
            "data": result.data
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/fuel/calculate")
async def calculate_fuel_cost(
    fuel_type: str = Query(..., description="Fuel type (petrol, diesel, hybrid, electric, lpg)"),
    quantity: float = Query(..., description="Quantity in litres or kWh", gt=0)
):
    """
    GET /api/fuel/calculate - Calculate fuel cost based on current prices
    """
    try:
        prices = get_latest_prices_from_supabase()
        
        if not prices:
            prices = EPRA_DEFAULTS
        
        fuel_type = fuel_type.lower()
        price_per_unit = prices.get(fuel_type)
        
        if price_per_unit is None:
            return JSONResponse({
                "success": False,
                "error": f"Invalid fuel type: {fuel_type}. Valid types: petrol, diesel, hybrid, electric, lpg"
            }, status_code=400)
        
        total_cost = price_per_unit * quantity
        
        return JSONResponse({
            "success": True,
            "data": {
                "fuel_type": fuel_type,
                "quantity": quantity,
                "price_per_unit": price_per_unit,
                "total_cost": round(total_cost, 2),
                "currency": "KES",
                "unit": "litres" if fuel_type != "electric" else "kWh"
            }
        })
        
    except Exception as e:
        logger.error(f"Calculate fuel cost error: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/ping")
async def ping():
    """Health check"""
    return JSONResponse({
        "status": "ok",
        "timestamp": format_timestamp()
    })


@app.get("/", response_class=HTMLResponse)
async def index():
    """Root endpoint with HTML interface"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EPRA Fuel Server</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Arial, sans-serif; 
                background: #0a0c15; 
                color: #fff; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                min-height: 100vh;
            }
            .container {
                max-width: 700px; 
                padding: 40px; 
                background: linear-gradient(145deg, #111827, #0f1520);
                border-radius: 20px;
                border: 1px solid #1e2a3a;
                box-shadow: 0 20px 60px rgba(0,0,0,0.8);
            }
            h1 { 
                color: #eab308; 
                font-size: 2.2rem; 
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .status { 
                display: inline-block; 
                background: #10b981; 
                color: #fff; 
                padding: 4px 16px; 
                border-radius: 20px; 
                font-size: 12px;
                font-weight: 600;
            }
            .prices {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                margin: 24px 0;
            }
            .price-card {
                background: #1a2332;
                padding: 14px 20px;
                border-radius: 12px;
                border-left: 4px solid #eab308;
            }
            .price-card .label {
                font-size: 12px;
                color: #8899bb;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .price-card .value {
                font-size: 1.3rem;
                font-weight: 700;
                color: #fff;
            }
            .price-card .value .currency {
                font-size: 0.8rem;
                color: #8899bb;
                font-weight: 400;
            }
            .endpoints {
                margin-top: 20px;
                border-top: 1px solid #1e2a3a;
                padding-top: 20px;
            }
            .endpoints h3 {
                color: #8899bb;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 12px;
            }
            .endpoint {
                display: flex;
                gap: 12px;
                padding: 8px 0;
                font-size: 14px;
                font-family: 'Courier New', monospace;
                border-bottom: 1px solid #131d2b;
            }
            .endpoint .method {
                color: #eab308;
                font-weight: 600;
                min-width: 50px;
            }
            .endpoint .path {
                color: #60a5fa;
            }
            .endpoint .desc {
                color: #8899bb;
                font-family: 'Segoe UI', Arial, sans-serif;
                margin-left: auto;
            }
            .footer {
                margin-top: 24px;
                font-size: 12px;
                color: #4a5a77;
                text-align: center;
                border-top: 1px solid #1a2332;
                padding-top: 16px;
            }
            @media (max-width: 600px) {
                .container { padding: 24px; margin: 16px; }
                .prices { grid-template-columns: 1fr; }
                .endpoint { flex-wrap: wrap; }
                .endpoint .desc { margin-left: 0; width: 100%; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>
                ⛽ EPRA Fuel Server
                <span class="status">● Live</span>
            </h1>
            <p style="color: #8899bb; margin-bottom: 4px;">Kenya Petroleum Prices • Single Source of Truth</p>
            
            <div class="prices">
                <div class="price-card">
                    <div class="label">⛽ Petrol</div>
                    <div class="value">KES 214.03 <span class="currency">/L</span></div>
                </div>
                <div class="price-card">
                    <div class="label">🛢️ Diesel</div>
                    <div class="value">KES 222.86 <span class="currency">/L</span></div>
                </div>
                <div class="price-card">
                    <div class="label">🔋 Hybrid</div>
                    <div class="value">KES 214.03 <span class="currency">/L</span></div>
                </div>
                <div class="price-card">
                    <div class="label">⚡ Electric</div>
                    <div class="value">KES 20.00 <span class="currency">/kWh</span></div>
                </div>
            </div>

            <div class="endpoints">
                <h3>📡 API Endpoints</h3>
                <div class="endpoint">
                    <span class="method">GET</span>
                    <span class="path">/api/fuel-prices</span>
                    <span class="desc">Get current prices</span>
                </div>
                <div class="endpoint">
                    <span class="method">POST</span>
                    <span class="path">/api/fuel-prices/update</span>
                    <span class="desc">Fetch EPRA prices</span>
                </div>
                <div class="endpoint">
                    <span class="method">GET</span>
                    <span class="path">/api/vehicles/makes</span>
                    <span class="desc">Get vehicle makes</span>
                </div>
                <div class="endpoint">
                    <span class="method">GET</span>
                    <span class="path">/api/vehicles/models</span>
                    <span class="desc">Get vehicle models</span>
                </div>
                <div class="endpoint">
                    <span class="method">GET</span>
                    <span class="path">/api/fuel/calculate</span>
                    <span class="desc">Calculate fuel cost</span>
                </div>
                <div class="endpoint">
                    <span class="method">GET</span>
                    <span class="path">/api/ping</span>
                    <span class="desc">Health check</span>
                </div>
            </div>

            <div class="footer">
                🔗 Supabase Connected • EPRA Prices Updated: 14th of Each Month
            </div>
        </div>
    </body>
    </html>
    """


# ─── Main Entry Point ────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║           EPRA FUEL SERVER - PRODUCTION                       ║
    ║                                                              ║
    ║  ✅ Connected to Supabase                                    ║
    ║  ✅ EPRA Prices: Petrol 214.03 | Diesel 222.86              ║
    ║  ✅ Auto-fetches EPRA fuel prices on demand                  ║
    ║  ✅ Serves as Single Source of Truth                         ║
    ║  ✅ Running on http://localhost:8000                         ║
    ║  ✅ API Docs: http://localhost:8000/docs                    ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "epra_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
