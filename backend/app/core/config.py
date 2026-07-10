# app/core/config.py
# =============================================================================
# AUTO-V API - Application Settings
# =============================================================================
"""
Single source of truth for configuration. Every other module reads settings
from here (`from app.core.config import settings`) instead of calling
os.getenv() directly. This is what prevents the "does settings.supabase_url
exist?" class of bugs — if a var isn't declared here, using it is a
clear AttributeError instead of a silent None.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Environment ─────────────────────────────────────────────
    environment: str = "production"
    debug: bool = False

    # ─── Supabase ────────────────────────────────────────────────
    # anon key: safe for client-side / RLS-respecting reads
    # service key: server-side only, bypasses RLS — used for all backend writes
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # ─── Auth / JWT ──────────────────────────────────────────────
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    refresh_token_expire_days: int = 30

    # ─── CORS ────────────────────────────────────────────────────
    # NOTE: must be explicit origins, not "*" — allow_credentials=True in
    # main.py means browsers will reject a wildcard origin outright.
    # Override in production via the CORS_ORIGINS env var, e.g.:
    #   CORS_ORIGINS=["https://auto-v.meipressgroup.com"]
    cors_origins: List[str] = [
        "https://auto-v.meipressgroup.com",
        "http://localhost:3000",
    ]

    # ─── M-Pesa ──────────────────────────────────────────────────
    mpesa_consumer_key: str = ""
    mpesa_consumer_secret: str = ""
    mpesa_shortcode: str = ""
    mpesa_passkey: str = ""
    mpesa_environment: str = "sandbox"
    mpesa_callback_url: str = ""

    # ─── Redis (rate limiting / caching) ────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ─── Misc ────────────────────────────────────────────────────
    api_v1_prefix: str = "/api/v1"
    project_name: str = "AUTO-V API"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — env is read once per process."""
    return Settings()


settings = get_settings()
