# app/api/v1/routes/settings.py
# =============================================================================
# AUTO-V API - Settings Routes
# =============================================================================
from fastapi import APIRouter

router = APIRouter(tags=["Settings"])

# NOTE: hardcoded placeholder settings. Replace with a real settings
# table/service once one exists — this just unblocks the frontend for now.
_SETTINGS = {
    "instant_fee": "500",
}


@router.get("/{setting_key}")
async def get_setting(setting_key: str):
    """
    Return a single app setting by key.
    Matches the shape the frontend expects: { setting_key, setting_value }
    """
    value = _SETTINGS.get(setting_key, None)
    return {
        "setting_key": setting_key,
        "setting_value": value,
    }


__all__ = ["router"]
