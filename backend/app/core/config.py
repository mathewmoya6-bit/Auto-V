# app/core/config.py
# =============================================================================
# AUTO-V API - Configuration Settings
# =============================================================================
# This module handles all application configuration using pydantic-settings.
# Values are loaded from environment variables or a .env file.
# All sensitive values MUST be set as environment variables in production.
# =============================================================================

import os
import json
import ast
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, ValidationInfo, Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All fields with no default value MUST be set in the environment.
    For production deployment on Render, these must be configured in
    the Render Dashboard under Environment Variables.
    """
    
    # =========================================================================
    # APP METADATA
    # =========================================================================
    APP_NAME: str = "AUTO-V API"
    APP_VERSION: str = "1.0.0"
    ENV: str = Field(default="production", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    
    # =========================================================================
    # SERVER CONFIGURATION
    # =========================================================================
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of workers for Gunicorn/Uvicorn")
    LOG_LEVEL: str = Field(default="info", description="Logging level: debug, info, warning, error, critical")
    
    # =========================================================================
    # API CONFIGURATION
    # =========================================================================
    API_V1_PREFIX: str = Field(default="/api/v1", description="API version 1 prefix")
    API_URL: str = Field(
        default="https://auto-v-backend.onrender.com",
        description="Public URL of the API"
    )
    
    # =========================================================================
    # CORS / SECURITY
    # =========================================================================
    # Accepts: JSON array ["a","b"] OR comma-separated "a,b" OR single "*"
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins (JSON array or comma-separated)"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["*"],
        description="Allowed hosts for the application (JSON array or comma-separated)"
    )
    
    # Security headers
    SECURE_SSL_REDIRECT: bool = Field(default=True, description="Redirect HTTP to HTTPS")
    SESSION_COOKIE_SECURE: bool = Field(default=True, description="Secure session cookies")
    CSRF_ENABLED: bool = Field(default=True, description="Enable CSRF protection")
    
    # ─── CORS_ORIGINS Validator ──────────────────────────────────────────
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """
        Parse CORS origins from various formats:
        - JSON array: ["a", "b", "c"]
        - Python list: ['a', 'b', 'c']
        - Comma-separated: "a,b,c"
        - Single value: "*"
        - Empty: returns ["*"]
        """
        if v is None or v == "":
            return ["*"]
        
        if isinstance(v, list):
            # Filter out empty strings and None
            return [item.strip() for item in v if item and str(item).strip()]
        
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return ["*"]
            
            # Try JSON parsing
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if item]
                return [str(parsed).strip()]
            except json.JSONDecodeError:
                pass
            
            # Try Python literal (ast.literal_eval)
            try:
                parsed = ast.literal_eval(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if item]
                return [str(parsed).strip()]
            except (ValueError, SyntaxError):
                pass
            
            # Fallback: comma-separated string
            if "," in v:
                return [item.strip() for item in v.split(",") if item.strip()]
            
            # Single value
            return [v]
        
        # Fallback for any other type
        return ["*"]
    
    # ─── ALLOWED_HOSTS Validator ──────────────────────────────────────────
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        """
        Parse allowed hosts from various formats:
        - JSON array: ["a", "b", "c"]
        - Python list: ['a', 'b', 'c']
        - Comma-separated: "a,b,c"
        - Single value: "*"
        - Empty: returns ["*"]
        """
        if v is None or v == "":
            return ["*"]
        
        if isinstance(v, list):
            return [item.strip() for item in v if item and str(item).strip()]
        
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return ["*"]
            
            # Try JSON parsing
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if item]
                return [str(parsed).strip()]
            except json.JSONDecodeError:
                pass
            
            # Try Python literal
            try:
                parsed = ast.literal_eval(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if item]
                return [str(parsed).strip()]
            except (ValueError, SyntaxError):
                pass
            
            # Fallback: comma-separated string
            if "," in v:
                return [item.strip() for item in v.split(",") if item.strip()]
            
            # Single value
            return [v]
        
        return ["*"]
    
    # =========================================================================
    # DATABASE
    # =========================================================================
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Database connection URL (async driver required)"
    )
    
    DB_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Database connection pool overflow")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Database connection pool timeout in seconds")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries for debugging")
    
    # =========================================================================
    # SUPABASE
    # =========================================================================
    SUPABASE_URL: Optional[str] = Field(
        default=None,
        description="Supabase project URL (e.g., https://xxxxx.supabase.co)"
    )
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(
        default=None,
        description="Supabase service role key (for admin operations)"
    )
    SUPABASE_JWT_SECRET: Optional[str] = Field(
        default=None,
        description="Supabase JWT secret for verifying session tokens"
    )
    SUPABASE_ANON_KEY: Optional[str] = Field(
        default=None,
        description="Supabase anonymous key (for client operations)"
    )
    
    # =========================================================================
    # JWT AUTHENTICATION
    # =========================================================================
    JWT_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="JWT secret key for local authentication"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiry in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiry in days")
    
    # =========================================================================
    # REDIS / CACHING
    # =========================================================================
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL (e.g., redis://localhost:6379)"
    )
    CACHE_TTL_SECONDS: int = Field(default=300, description="Default cache TTL in seconds")
    
    # =========================================================================
    # EMAIL CONFIGURATION
    # =========================================================================
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_FROM_EMAIL: Optional[str] = Field(default=None, description="Sender email address")
    SMTP_FROM_NAME: str = Field(default="AUTO-V", description="Sender display name")
    SMTP_USE_TLS: bool = Field(default=True, description="Use TLS for SMTP")
    SMTP_USE_SSL: bool = Field(default=False, description="Use SSL for SMTP")
    
    # =========================================================================
    # RATE LIMITING
    # =========================================================================
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Rate limit: requests per minute")
    RATE_LIMIT_PER_DAY: int = Field(default=1000, description="Rate limit: requests per day")
    
    # =========================================================================
    # FILE UPLOAD
    # =========================================================================
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, description="Maximum file upload size in MB")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["jpg", "jpeg", "png", "pdf", "doc", "docx"],
        description="Allowed file extensions"
    )
    UPLOAD_DIR: str = Field(default="./uploads", description="Upload directory path")
    
    # =========================================================================
    # LOGGING
    # =========================================================================
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    # =========================================================================
    # EXTERNAL SERVICES
    # =========================================================================
    # Add any external service API keys here
    
    # =========================================================================
    # FEATURE FLAGS
    # =========================================================================
    ENABLE_SWAGGER: bool = Field(default=True, description="Enable Swagger documentation")
    ENABLE_EMAIL: bool = Field(default=True, description="Enable email sending")
    ENABLE_CACHING: bool = Field(default=True, description="Enable Redis caching")
    ENABLE_RATE_LIMITING: bool = Field(default=True, description="Enable rate limiting")
    
    # =========================================================================
    # PYDANTIC CONFIGURATION
    # =========================================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENV.lower() in ["dev", "development", "local"]
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENV.lower() in ["prod", "production"]
    
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.ENV.lower() in ["stage", "staging"]
    
    def database_configured(self) -> bool:
        """Check if database URL is configured."""
        return self.DATABASE_URL is not None and self.DATABASE_URL != ""
    
    def supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return (
            self.SUPABASE_URL is not None and self.SUPABASE_URL != "" and
            self.SUPABASE_SERVICE_ROLE_KEY is not None and self.SUPABASE_SERVICE_ROLE_KEY != ""
        )
    
    def redis_configured(self) -> bool:
        """Check if Redis is configured."""
        return self.REDIS_URL is not None and self.REDIS_URL != ""


# =============================================================================
# INSTANTIATE SETTINGS
# =============================================================================
settings = Settings()

# =============================================================================
# VALIDATE CRITICAL SETTINGS ON STARTUP
# =============================================================================
def validate_settings():
    """
    Validate critical settings and raise warnings/errors if required
    values are missing in production.
    """
    if settings.is_production():
        # Database is required in production
        if not settings.database_configured():
            print("⚠️  WARNING: DATABASE_URL is not set in production!")
            print("   - Set DATABASE_URL in your Render environment variables")
            print("   - Format: postgresql+asyncpg://user:pass@host:5432/dbname")
        
        # Supabase is recommended in production
        if not settings.supabase_configured():
            print("⚠️  WARNING: Supabase credentials are not fully configured!")
            print("   - Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_JWT_SECRET")
        
        # JWT secret should be set
        if not settings.JWT_SECRET_KEY:
            print("⚠️  WARNING: JWT_SECRET_KEY is not set! Using default (INSECURE)")
            print("   - Set JWT_SECRET_KEY in your Render environment variables")
            print("   - Use a strong secret key (32+ characters)")


# Run validation on import
validate_settings()


# =============================================================================
# HELPER: Get database connection string with proper driver
# =============================================================================
def get_database_url(default_driver: str = "asyncpg") -> Optional[str]:
    """
    Get the database URL with the specified driver.
    
    Args:
        default_driver: The driver to use (e.g., 'asyncpg', 'psycopg')
    
    Returns:
        The database URL with the appropriate driver, or None if not configured.
    """
    if not settings.database_configured():
        return None
    
    url = settings.DATABASE_URL
    
    # If using PostgreSQL without a driver specified, add the async driver
    if url.startswith("postgresql://") and "+" not in url:
        return url.replace("postgresql://", f"postgresql+{default_driver}://")
    
    return url


# =============================================================================
# HELPER: Get CORS origins for FastAPI
# =============================================================================
def get_cors_origins() -> List[str]:
    """
    Get CORS origins with fallbacks for different environments.
    """
    origins = settings.CORS_ORIGINS
    
    # Ensure we have valid origins
    if not origins or origins == []:
        return ["*"]
    
    # In development, allow all
    if settings.is_development():
        return ["*"]
    
    return origins


# =============================================================================
# HELPER: Get allowed hosts for security
# =============================================================================
def get_allowed_hosts() -> List[str]:
    """
    Get allowed hosts with environment-specific fallbacks.
    """
    hosts = settings.ALLOWED_HOSTS
    
    # Ensure we have valid hosts
    if not hosts or hosts == []:
        return ["*"]
    
    # In production with wildcard, use specific hosts
    if hosts == ["*"] and settings.is_production():
        return [
            "auto-v-backend.onrender.com",
            "auto-v.meipressgroup.com",
            "www.auto-v.meipressgroup.com",
        ]
    
    return hosts


# =============================================================================
# HELPER: Get log level for different environments
# =============================================================================
def get_log_level() -> str:
    """
    Get the appropriate log level based on environment.
    """
    if settings.is_development():
        return "debug"
    return settings.LOG_LEVEL
