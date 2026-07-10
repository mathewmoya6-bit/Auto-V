# app/schemas/settings.py
"""
App-wide settings (key/value), e.g. instant_fee, valuation weightings, etc.
Not user-specific — these are global config values editable by admins.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class SettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: Any
    description: Optional[str] = None
    updated_at: datetime


class SettingUpdate(BaseModel):
    value: Any
