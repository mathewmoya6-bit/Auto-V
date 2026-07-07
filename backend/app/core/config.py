# app/core/config.py
# =============================================================================
# AUTO-V API - Configuration
# =============================================================================

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # ─── Application ──────────────────────────────────────────────────
    APP_NAME: str = "AUTO-V API"
    APP_VERSION: str = "3.1.0"
    ENV: str = "production"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # ─── Supabase ────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    # ─── JWT ─────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ─── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # ─── Logging ─────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json, text
    
    # ─── Feature Flags ──────────────────────────────────────────────
    ENABLE_SWAGGER: bool = True
    ENABLE_METRICS: bool = False
    
    # ─── Pydantic v2 Configuration ───────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # ─── Properties ──────────────────────────────────────────────────
    @property
    def is_development(self) -> bool:
        return self.ENV.lower() in ["development", "dev"]
    
    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"
    
    @property
    def supabase_configured(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_ANON_KEY)


settings = Settings()
