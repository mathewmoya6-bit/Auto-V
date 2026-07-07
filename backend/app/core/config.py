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
    ENV: str = "production"  # development, staging, production
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
    
    # ─── Database ────────────────────────────────────────────────────
    DATABASE_URL: Optional[str] = None
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    
    # ─── Storage ─────────────────────────────────────────────────────
    STORAGE_PROVIDER: str = "supabase"  # supabase, s3, local
    STORAGE_BUCKET: str = "autov-storage"
    STORAGE_PUBLIC_URL: str = ""
    
    # ─── AI / ML ─────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    GOOGLE_VISION_API_KEY: str = ""
    CARAPI_KEY: str = ""
    
    # ─── Email (SMTP) ────────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@autov.africa"
    SMTP_TLS: bool = True
    
    # ─── Redis / Cache ──────────────────────────────────────────────
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 300
    
    # ─── Logging ─────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json, text
    
    # ─── Feature Flags ──────────────────────────────────────────────
    ENABLE_SWAGGER: bool = True
    ENABLE_METRICS: bool = False
    ENABLE_EMAIL_VERIFICATION: bool = True
    
    # ─── Pydantic v2 Configuration ───────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra env vars not defined here
    )
    
    # ─── Computed Properties ────────────────────────────────────────
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENV.lower() in ["development", "dev"]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENV.lower() == "production"
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging mode."""
        return self.ENV.lower() == "staging"
    
    @property
    def database_configured(self) -> bool:
        """Check if database is configured."""
        return bool(self.DATABASE_URL)
    
    @property
    def supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.SUPABASE_URL and self.SUPABASE_ANON_KEY)


# ─── Singleton Instance ─────────────────────────────────────────────
settings = Settings()


# ─── Quick Validation on Import ────────────────────────────────────
if settings.JWT_SECRET_KEY in ["your-secret-key", "your-secret-key-change-in-production"]:
    import warnings
    warnings.warn(
        "⚠️ JWT_SECRET_KEY is using a default value! "
        "Please set a secure secret key in your .env file.",
        UserWarning
    )
