# app/routers/settings.py
# =============================================================================
# AUTO-V API - Settings Router
# =============================================================================
# Public, read-only config values the frontend needs (e.g. service fees).
# No auth required — these are not user-specific or sensitive.
# =============================================================================
import os
from fastapi import APIRouter

router = APIRouter(prefix="/settings", tags=["settings"])

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
        "currency": "KES"
    }
