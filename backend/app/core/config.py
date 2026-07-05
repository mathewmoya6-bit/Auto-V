# app/core/config.py
# =============================================================================
# AUTO-V API - Settings
# =============================================================================

from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # ============================================================
    # APPLICATION
    # ============================================================
    
    APP_NAME: str = Field(default="AUTO-V Professional Valuation Engine")
    APP_VERSION: str = Field(default="2.0.0")
    ENV: str = Field(default="production")
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=10000)
    API_V1_PREFIX: str = Field(default="/api/v1")
    PROJECT_NAME: str = Field(default="AUTO-V API")

    # ============================================================
    # DATABASE (Supabase PostgreSQL)
    # ============================================================
    
    DATABASE_URL: str = Field(default="", description="Supabase Postgres connection string")
    
    # ============================================================
    # SUPABASE
    # ============================================================
    
    SUPABASE_URL: str = Field(default="")
    SUPABASE_ANON_KEY: str = Field(default="")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="")
    SUPABASE_JWT_SECRET: str = Field(default="")
    
    # ============================================================
    # SECURITY
    # ============================================================
    
    SECRET_KEY: str = Field(default="")
    JWT_SECRET: str = Field(default="")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)
    
    # ============================================================
    # CORS
    # ============================================================
    
    CORS_ORIGINS: List[str] = Field(default=["*"])
    ALLOWED_HOSTS: List[str] = Field(default=["*"])
    
    # ============================================================
    # REDIS
    # ============================================================
    
    REDIS_ENABLED: bool = Field(default=True)
    REDIS_URL: str = Field(default="redis://localhost:6379")
    REDIS_MAX_CONNECTIONS: int = Field(default=10)
    REDIS_TTL: int = Field(default=3600)
    
    # ============================================================
    # RATE LIMITING
    # ============================================================
    
    RATELIMIT_ENABLED: bool = Field(default=True)
    RATELIMIT_DEFAULT: str = Field(default="100/minute")
    RATELIMIT_STORAGE_URI: str = Field(default="redis://localhost:6379")
    MAX_LOGIN_ATTEMPTS: int = Field(default=5)
    IP_RATE_LIMIT: int = Field(default=100)
    
    # ============================================================
    # LOGGING
    # ============================================================
    
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    
    # ============================================================
    # AI SERVICES
    # ============================================================
    
    AI_WEIGHT: float = Field(default=0.4)
    AI_MIN_CONFIDENCE: float = Field(default=0.3)
    AI_CACHE_ENABLED: bool = Field(default=True)
    AI_FALLBACK_ENABLED: bool = Field(default=True)
    AI_PREDICTIONS_ENABLED: bool = Field(default=True)
    AI_CACHE_TTL: int = Field(default=3600)
    
    # ============================================================
    # FEATURES
    # ============================================================
    
    FEATURE_MPESA: bool = Field(default=True)
    FEATURE_VIN_AUTOFILL: bool = Field(default=True)
    FEATURE_AI_VALUATION: bool = Field(default=True)
    FEATURE_FRAUD_DETECTION: bool = Field(default=True)
    FEATURE_DOCUMENT_VERIFICATION: bool = Field(default=True)
    FEATURE_REPORT_GENERATION: bool = Field(default=True)
    FEATURE_QR_VERIFICATION: bool = Field(default=True)
    ENABLE_IMAGE_ANALYSIS: bool = Field(default=True)
    ENABLE_DOCUMENT_OCR: bool = Field(default=True)
    ENABLE_PRICE_PREDICTION: bool = Field(default=True)
    ENABLE_CHAT_ASSISTANT: bool = Field(default=True)
    REALTIME_ENABLED: bool = Field(default=True)
    
    # ============================================================
    # STORAGE
    # ============================================================
    
    STORAGE_TYPE: str = Field(default="supabase")
    STORAGE_BUCKET: str = Field(default="autov-storage")
    MAX_IMAGE_SIZE: int = Field(default=10485760)  # 10MB
    MAX_DOCUMENT_SIZE: int = Field(default=20971520)  # 20MB
    
    # ============================================================
    # VEHICLE DATA API
    # ============================================================
    
    CARAPI_KEY: str = Field(default="")
    
    # ============================================================
    # EXTERNAL API KEYS
    # ============================================================
    
    OPENAI_API_KEY: str = Field(default="")
    GOOGLE_VISION_API_KEY: str = Field(default="")
    
    # ============================================================
    # EMAIL
    # ============================================================
    
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USERNAME: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    SMTP_FROM_EMAIL: str = Field(default="")
    SMTP_TLS: bool = Field(default=True)
    
    # ============================================================
    # REALTIME
    # ============================================================
    
    REALTIME_HEARTBEAT_INTERVAL: int = Field(default=30)
    REALTIME_RETRY_ATTEMPTS: int = Field(default=3)
    REALTIME_RETRY_DELAY: int = Field(default=2)
    REALTIME_MAX_CHANNELS: int = Field(default=100)
    
    # ============================================================
    # PAYMENT WORKER
    # ============================================================
    
    PAYMENT_WORKER_ENABLED: bool = Field(default=True)
    PAYMENT_WORKER_INTERVAL: int = Field(default=60)
    PAYMENT_RETRY_MAX: int = Field(default=3)
    PAYMENT_RETRY_DELAY: int = Field(default=60)
    
    # ============================================================
    # WEBHOOKS
    # ============================================================
    
    WEBHOOK_RETRY_MAX: int = Field(default=3)
    WEBHOOK_RETRY_DELAY: int = Field(default=30)
    WEBHOOK_TIMEOUT: int = Field(default=30)
    
    # ============================================================
    # DATABASE POOL
    # ============================================================
    
    DB_POOL_SIZE: int = Field(default=10)
    DB_MAX_OVERFLOW: int = Field(default=20)
    DB_POOL_TIMEOUT: int = Field(default=30)
    
    # ============================================================
    # SESSION
    # ============================================================
    
    SESSION_TIMEOUT_MINUTES: int = Field(default=60)
    SESSION_COOKIE_SECURE: bool = Field(default=True)
    SESSION_COOKIE_HTTPONLY: bool = Field(default=True)
    
    # ============================================================
    # SSL
    # ============================================================
    
    SSL_ENABLED: bool = Field(default=False)
    
    # ============================================================
    # MAINTENANCE
    # ============================================================
    
    MAINTENANCE_MODE: bool = Field(default=False)
    MAINTENANCE_MESSAGE: str = Field(default="System is currently undergoing maintenance. Please try again later.")
    
    # ============================================================
    # VALIDATORS
    # ============================================================
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from string or list."""
        if isinstance(v, str):
            # Handle both JSON array format and comma-separated
            if v.startswith("[") and v.endswith("]"):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from string or list."""
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                return json.loads(v)
            return [host.strip() for host in v.split(",") if host.strip()]
        return v
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        """Ensure DATABASE_URL is a string."""
        if v and isinstance(v, str):
            return v.strip('"').strip("'")
        return v

    # ============================================================
    # HELPER METHODS
    # ============================================================
    
    def database_configured(self) -> bool:
        """Check if database is configured."""
        return bool(self.DATABASE_URL)
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENV.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENV.lower() in ["development", "dev"]
    
    def get_database_async_url(self) -> str:
        """Get async database URL."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# ============================================================
# SINGLETON INSTANCE
# ============================================================

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Create a single instance
settings = get_settings()
