# app/core/config.py
# Settings inferred from every `settings.X` reference in main.py.
# Uses pydantic-settings so values load from environment variables /
# a .env file automatically. Adjust defaults as needed — these are
# reasonable starting points, not guarantees of what your Render
# environment actually has set.

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    # ─── App metadata ──────────────────────────────────────────
    APP_NAME: str = "AUTO-V API"
    APP_VERSION: str = "1.0.0"
    ENV: str = "production"
    DEBUG: bool = False

    # ─── Server ─────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    LOG_LEVEL: str = "info"

    # ─── API ────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    API_URL: str = "https://auto-v-backend.onrender.com"

    # ─── CORS / Security ────────────────────────────────────────
    # Comma-separated in the env var, e.g.
    # CORS_ORIGINS=https://auto-v.meipressgroup.com,http://localhost:3000
    CORS_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]

    # ─── Database ───────────────────────────────────────────────
    # Async driver required (asyncpg) since database.py uses
    # SQLAlchemy's async engine. Example:
    # postgresql+asyncpg://user:password@host:5432/dbname
    DATABASE_URL: str

    # ─── Supabase (used for auth/session verification against the
    # same project the frontend talks to directly) ───────────────
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None  # needed to verify
    # frontend-issued Supabase session JWTs on protected routes

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
