"""
EPRA Fuel Price Server - Production Ready (v2)
Integrates with Supabase as Single Source of Truth
FastAPI Version - Complete Standalone Server

Key changes from v1 (see inline comments for detail on each):
  1. All blocking I/O (requests.get, Supabase client calls) now runs via
     asyncio.to_thread() instead of directly inside async def -- v1 blocked
     the entire event loop on every single call, serializing all traffic.
  2. Price saves are now append-only (INSERT), not update-in-place --
     v1's read path already assumed history ("order by updated_at desc,
     limit 1") but the write path silently destroyed that history by
     UPDATEing the one existing row instead of inserting a new one.
  3. Scraped prices are sanity-checked against a plausible range before
     being trusted -- a regex match against the wrong part of the page
     could previously have saved a garbage price with no warning.
  4. CORS no longer combines allow_origins=["*"] with allow_credentials=True
     -- that combination is invalid per the CORS spec and browsers reject
     or strip credentials from it silently, which is worse than either
     option alone since it looks configured but doesn't work as intended.
  5. The mutating endpoint (/api/fuel-prices/update) now requires a shared
     API key header -- it scrapes an external site and writes to your DB,
     and was previously open to anyone on the internet to trigger.
  6. Error handling is standardized on HTTPException + logging everywhere,
     instead of a mix of typed Pydantic error responses in some routes and
     raw JSONResponse dicts with inconsistent shapes in others.
  7. Supabase credentials are required from the environment, not hardcoded
     as Python defaults -- baking a live project's URL+key into source
     couples this file to one specific project and risks silent use of
     stale/wrong credentials if copied elsewhere.
  8. fuel_type is now validated against a Literal type for proper OpenAPI
     docs and 422 validation, instead of accepted as a bare string.
"""

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from supabase import Client, create_client

# ─── Configuration ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("epra_fuel_server")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be set in the environment. "
        "Refusing to start with no configured Supabase credentials -- "
        "silently falling back to a hardcoded project is not safe."
    )

# Shared secret required on the mutating endpoint (POST /api/fuel-prices/update).
# Set this in your environment; requests without a matching X-API-Key header
# are rejected with 401. Leave EPRA_UPDATE_API_KEY unset locally to disable
# the check during development (a warning is logged so this isn't silent).
EPRA_UPDATE_API_KEY = os.getenv("EPRA_UPDATE_API_KEY")
if not EPRA_UPDATE_API_KEY:
    logger.warning(
        "EPRA_UPDATE_API_KEY is not set -- POST /api/fuel-prices/update is "
        "UNPROTECTED. Set this env var before deploying to production."
    )

# Comma-separated list of allowed origins, e.g.
# CORS_ORIGINS=https://auto-v.meipressgroup.com,https://www.auto-v.meipressgroup.com
_cors_origins_env = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS = [o.strip() for o in _cors_origins_env.split(",") if o.strip()] or ["*"]

# EPRA Default Prices (fallback reference point, updated ~14th of each month
# by EPRA -- these are a last-resort fallback, not meant to silently drift
# out of date forever; refresh this dict periodically even if scraping works)
EPRA_DEFAULTS: Dict[str, float] = {
    "petrol": 214.03,
    "diesel": 222.86,
    "hybrid": 214.03,
    "lpg": 120.00,
    "electric": 20.00,
    "kerosene": 163.00,
}

EPRA_URL = "https://www.epra.go.ke/petroleum-prices/"

# Sanity bounds (KES) -- a scraped value outside this range is almost
# certainly a mis-parsed fragment of the page, not a real price.
_PRICE_SANITY_BOUNDS = {
    "petrol": (50.0, 500.0),
    "diesel": (50.0, 500.0),
    "kerosene": (30.0, 400.0),
}


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


class FuelCalculationResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ─── Initialize Clients ─────────────────────────────────────

app = FastAPI(
    title="EPRA Fuel Price Server",
    version="2.0.0",
    description="Kenya fuel price server with Supabase as single source of truth",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    # Only allow credentials when origins are explicitly restricted --
    # combining "*" with allow_credentials=True is invalid per the CORS
    # spec and browsers will reject/strip it rather than honor it.
    allow_credentials=CORS_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─── Auth dependency for the mutating endpoint ─────────────────

async def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if not EPRA_UPDATE_API_KEY:
        # Explicitly unprotected in this environment; already warned at
        # startup. Don't silently 401 in dev with no way to configure it.
        return
    if x_api_key != EPRA_UPDATE_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing X-API-Key header")


# ─── Helper Functions ──────────────────────────────────────────

def format_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_epra_defaults() -> Dict[str, float]:
    return EPRA_DEFAULTS.copy()


def _is_plausible_price(fuel_type: str, value: Optional[float]) -> bool:
    if value is None:
        return False
    bounds = _PRICE_SANITY_BOUNDS.get(fuel_type)
    if bounds is None:
        return True  # no bounds configured for this fuel type, accept as-is
    low, high = bounds
    return low <= value <= high


def _fetch_epra_prices_sync() -> Dict[str, float]:
    """Blocking implementation -- always call via asyncio.to_thread, never
    directly from an async def route."""
    try:
        response = requests.get(
            EPRA_URL,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )

        if response.status_code != 200:
            logger.warning("EPRA site returned HTTP %s, using defaults", response.status_code)
            return get_epra_defaults()

        html = response.text.lower()

        petrol_match = re.search(r"petrol[^0-9]*(\d+\.?\d*)", html)
        diesel_match = re.search(r"diesel[^0-9]*(\d+\.?\d*)", html)
        kerosene_match = re.search(r"kerosene[^0-9]*(\d+\.?\d*)", html)

        petrol = float(petrol_match.group(1)) if petrol_match else None
        diesel = float(diesel_match.group(1)) if diesel_match else None
        kerosene = float(kerosene_match.group(1)) if kerosene_match else None

        if not _is_plausible_price("petrol", petrol):
            logger.warning("Scraped petrol price %s failed sanity check, discarding", petrol)
            petrol = None
        if not _is_plausible_price("diesel", diesel):
            logger.warning("Scraped diesel price %s failed sanity check, discarding", diesel)
            diesel = None
        if kerosene is not None and not _is_plausible_price("kerosene", kerosene):
            logger.warning("Scraped kerosene price %s failed sanity check, discarding", kerosene)
            kerosene = None

        if petrol and diesel:
            return {
                "petrol": petrol,
                "diesel": diesel,
                "hybrid": petrol,
                "lpg": EPRA_DEFAULTS.get("lpg", 120.00),
                "electric": EPRA_DEFAULTS.get("electric", 20.00),
                "kerosene": kerosene or EPRA_DEFAULTS.get("kerosene", 163.00),
            }

        logger.warning("Could not confidently parse petrol+diesel from EPRA page, using defaults")

    except requests.exceptions.Timeout:
        logger.warning("EPRA fetch timed out, using defaults")
    except requests.exceptions.RequestException as e:
        logger.warning("EPRA fetch error: %s", e)
    except Exception:
        logger.exception("Unexpected EPRA parse error")

    return get_epra_defaults()


def _save_prices_to_supabase_sync(prices: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """Blocking implementation -- always call via asyncio.to_thread.

    Appends a new row rather than updating the existing one, so historical
    prices are preserved. The read path already assumed this (it orders by
    updated_at desc and takes the latest); v1's write path contradicted
    that by overwriting the single row in place.
    """
    try:
        data = {
            "petrol": prices.get("petrol"),
            "diesel": prices.get("diesel"),
            "hybrid": prices.get("hybrid"),
            "lpg": prices.get("lpg"),
            "electric": prices.get("electric"),
            "kerosene": prices.get("kerosene"),
            "updated_at": format_timestamp(),
        }
        result = supabase.table("fuel_prices").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception:
        logger.exception("Supabase save error")
        return None


def _get_latest_prices_from_supabase_sync() -> Optional[Dict[str, Any]]:
    """Blocking implementation -- always call via asyncio.to_thread."""
    try:
        result = (
            supabase.table("fuel_prices")
            .select("*")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception:
        logger.exception("Supabase fetch error")
        return None


def _get_vehicle_makes_sync() -> list:
    return supabase.table("vehicle_makes").select("*").order("name").execute().data


def _get_vehicle_models_sync(make_id: Optional[int]) -> list:
    query = supabase.table("vehicle_models").select("*").order("name")
    if make_id:
        query = query.eq("make_id", make_id)
    return query.execute().data


# ─── Routes ──────────────────────────────────────────────────

@app.get("/api/fuel-prices", response_model=FuelPriceResponse)
async def get_prices():
    """GET /api/fuel-prices - current fuel prices from Supabase (or EPRA defaults)."""
    try:
        saved = await asyncio.to_thread(_get_latest_prices_from_supabase_sync)

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
                    "source": "supabase",
                },
                timestamp=format_timestamp(),
            )

        return FuelPriceResponse(
            success=True,
            data={**EPRA_DEFAULTS, "last_updated": format_timestamp(), "source": "epra_defaults"},
            timestamp=format_timestamp(),
        )

    except Exception as e:
        logger.exception("Get prices error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/fuel-prices/update", response_model=FuelPriceUpdateResponse, dependencies=[Depends(require_api_key)])
async def update_prices():
    """POST /api/fuel-prices/update - fetch EPRA prices and append to Supabase.

    Requires X-API-Key header matching EPRA_UPDATE_API_KEY (see startup log
    if that's not configured). This hits an external site and writes to
    your database, so it isn't left open to anonymous callers.
    """
    try:
        prices = await asyncio.to_thread(_fetch_epra_prices_sync)
        saved = await asyncio.to_thread(_save_prices_to_supabase_sync, prices)

        if saved:
            return FuelPriceUpdateResponse(success=True, message="Fuel prices updated successfully", data=prices)

        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to save prices to Supabase")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Update prices error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/vehicles/makes")
async def get_makes():
    """GET /api/vehicles/makes - all vehicle makes."""
    try:
        data = await asyncio.to_thread(_get_vehicle_makes_sync)
        return {"success": True, "data": data}
    except Exception as e:
        logger.exception("Get makes error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/vehicles/models")
async def get_models(make_id: Optional[int] = None):
    """GET /api/vehicles/models?make_id=1 - models, optionally filtered by make."""
    try:
        data = await asyncio.to_thread(_get_vehicle_models_sync, make_id)
        return {"success": True, "data": data}
    except Exception as e:
        logger.exception("Get models error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/fuel/calculate", response_model=FuelCalculationResponse)
async def calculate_fuel_cost(
    fuel_type: Literal["petrol", "diesel", "hybrid", "electric", "lpg", "kerosene"] = Query(
        ..., description="Fuel type"
    ),
    quantity: float = Query(..., description="Quantity in litres or kWh", gt=0),
):
    """GET /api/fuel/calculate - cost for a quantity of fuel at current prices."""
    try:
        prices = await asyncio.to_thread(_get_latest_prices_from_supabase_sync)
        if not prices:
            prices = EPRA_DEFAULTS

        price_per_unit = prices.get(fuel_type)
        if price_per_unit is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No price on record for fuel type: {fuel_type}",
            )

        total_cost = float(price_per_unit) * quantity

        return FuelCalculationResponse(
            success=True,
            data={
                "fuel_type": fuel_type,
                "quantity": quantity,
                "price_per_unit": float(price_per_unit),
                "total_cost": round(total_cost, 2),
                "currency": "KES",
                "unit": "kWh" if fuel_type == "electric" else "litres",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Calculate fuel cost error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/ping")
async def ping():
    """Health check."""
    return {"status": "ok", "timestamp": format_timestamp()}


@app.get("/", response_class=HTMLResponse)
async def index():
    """Root endpoint with a small status dashboard.

    Prices shown here are live EPRA_DEFAULTS values (not hardcoded numbers
    baked into the markup), so this can't silently drift out of sync with
    the actual fallback values used elsewhere in this file.
    """
    d = EPRA_DEFAULTS
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EPRA Fuel Server</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: #0a0c15;
                color: #fff;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .container {{
                max-width: 700px;
                padding: 40px;
                background: linear-gradient(145deg, #111827, #0f1520);
                border-radius: 20px;
                border: 1px solid #1e2a3a;
                box-shadow: 0 20px 60px rgba(0,0,0,0.8);
            }}
            h1 {{
                color: #eab308;
                font-size: 2.2rem;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .status {{
                display: inline-block;
                background: #10b981;
                color: #fff;
                padding: 4px 16px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            .prices {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                margin: 24px 0;
            }}
            .price-card {{
                background: #1a2332;
                padding: 14px 20px;
                border-radius: 12px;
                border-left: 4px solid #eab308;
            }}
            .price-card .label {{
                font-size: 12px;
                color: #8899bb;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .price-card .value {{
                font-size: 1.3rem;
                font-weight: 700;
                color: #fff;
            }}
            .price-card .value .currency {{
                font-size: 0.8rem;
                color: #8899bb;
                font-weight: 400;
            }}
            .endpoints {{
                margin-top: 20px;
                border-top: 1px solid #1e2a3a;
                padding-top: 20px;
            }}
            .endpoints h3 {{
                color: #8899bb;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 12px;
            }}
            .endpoint {{
                display: flex;
                gap: 12px;
                padding: 8px 0;
                font-size: 14px;
                font-family: 'Courier New', monospace;
                border-bottom: 1px solid #131d2b;
            }}
            .endpoint .method {{ color: #eab308; font-weight: 600; min-width: 50px; }}
            .endpoint .path {{ color: #60a5fa; }}
            .endpoint .desc {{ color: #8899bb; font-family: 'Segoe UI', Arial, sans-serif; margin-left: auto; }}
            .footer {{
                margin-top: 24px;
                font-size: 12px;
                color: #4a5a77;
                text-align: center;
                border-top: 1px solid #1a2332;
                padding-top: 16px;
            }}
            @media (max-width: 600px) {{
                .container {{ padding: 24px; margin: 16px; }}
                .prices {{ grid-template-columns: 1fr; }}
                .endpoint {{ flex-wrap: wrap; }}
                .endpoint .desc {{ margin-left: 0; width: 100%; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⛽ EPRA Fuel Server <span class="status">● Live</span></h1>
            <p style="color: #8899bb; margin-bottom: 4px;">Kenya Petroleum Prices &middot; Single Source of Truth</p>

            <div class="prices">
                <div class="price-card"><div class="label">⛽ Petrol</div><div class="value">KES {d['petrol']:.2f} <span class="currency">/L</span></div></div>
                <div class="price-card"><div class="label">🛢️ Diesel</div><div class="value">KES {d['diesel']:.2f} <span class="currency">/L</span></div></div>
                <div class="price-card"><div class="label">🔋 Hybrid</div><div class="value">KES {d['hybrid']:.2f} <span class="currency">/L</span></div></div>
                <div class="price-card"><div class="label">⚡ Electric</div><div class="value">KES {d['electric']:.2f} <span class="currency">/kWh</span></div></div>
            </div>

            <div class="endpoints">
                <h3>📡 API Endpoints</h3>
                <div class="endpoint"><span class="method">GET</span><span class="path">/api/fuel-prices</span><span class="desc">Get current prices</span></div>
                <div class="endpoint"><span class="method">POST</span><span class="path">/api/fuel-prices/update</span><span class="desc">Fetch EPRA prices (requires X-API-Key)</span></div>
                <div class="endpoint"><span class="method">GET</span><span class="path">/api/vehicles/makes</span><span class="desc">Get vehicle makes</span></div>
                <div class="endpoint"><span class="method">GET</span><span class="path">/api/vehicles/models</span><span class="desc">Get vehicle models</span></div>
                <div class="endpoint"><span class="method">GET</span><span class="path">/api/fuel/calculate</span><span class="desc">Calculate fuel cost</span></div>
                <div class="endpoint"><span class="method">GET</span><span class="path">/api/ping</span><span class="desc">Health check</span></div>
            </div>

            <div class="footer">🔗 Supabase Connected &middot; EPRA prices refreshed on demand via POST /api/fuel-prices/update</div>
        </div>
    </body>
    </html>
    """


# ─── Main Entry Point ────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    d = EPRA_DEFAULTS
    print(f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║           EPRA FUEL SERVER - PRODUCTION (v2)                  ║
    ║                                                               ║
    ║  ✅ Connected to Supabase                                     ║
    ║  ✅ EPRA Defaults: Petrol {d['petrol']:.2f} | Diesel {d['diesel']:.2f}         ║
    ║  ✅ Non-blocking I/O (asyncio.to_thread)                      ║
    ║  ✅ Append-only price history                                 ║
    ║  {'✅' if EPRA_UPDATE_API_KEY else '⚠️ '} Update endpoint {'protected' if EPRA_UPDATE_API_KEY else 'UNPROTECTED - set EPRA_UPDATE_API_KEY'}
    ║  ✅ Running on http://localhost:8000                          ║
    ║  ✅ API Docs: http://localhost:8000/docs                     ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "epra_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
        log_level="info",
    )
