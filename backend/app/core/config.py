# app/core/config.py
# =============================================================================
# AUTO-V API - Configuration Settings
# =============================================================================

import os
import json
import ast
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # ─── APP METADATA ──────────────────────────────────────────────────
    APP_NAME: str = "AUTO-V API"
    APP_VERSION: str = "1.0.0"
    ENV: str = Field(default="production", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    
    # ─── SERVER CONFIGURATION ────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of workers")
    LOG_LEVEL: str = Field(default="info", description="Logging level")
    
    # ─── API CONFIGURATION ────────────────────────────────────────────
    API_V1_PREFIX: str = Field(default="/api/v1", description="API version 1 prefix")
    API_URL: str = Field(
        default="https://auto-v.onrender.com",
        description="Public URL of the API"
    )
    
    # ─── CORS / SECURITY ──────────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(
        default=[
            "https://auto-v.meipressgroup.com",
            "https://www.auto-v.meipressgroup.com",
            "https://auto-v.onrender.com",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5500",
        ],
        description="Allowed CORS origins"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=[
            "auto-v.meipressgroup.com",
            "www.auto-v.meipressgroup.com",
            "auto-v.onrender.com",
            "auto-v-backend.onrender.com",
            "localhost",
            "127.0.0.1",
        ],
        description="Allowed hosts for the application"
    )
    
    SECURE_SSL_REDIRECT: bool = Field(default=False, description="Redirect HTTP to HTTPS")
    SESSION_COOKIE_SECURE: bool = Field(default=True, description="Secure session cookies")
    CSRF_ENABLED: bool = Field(default=True, description="Enable CSRF protection")
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from various formats."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return ["*"]
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return [str(parsed)]
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(v)
                    if isinstance(parsed, list):
                        return parsed
                    return [str(parsed)]
                except (ValueError, SyntaxError):
                    if "," in v:
                        return [item.strip() for item in v.split(",") if item.strip()]
                    return [v]
        return ["*"]
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse allowed hosts from various formats."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return ["*"]
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return [str(parsed)]
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(v)
                    if isinstance(parsed, list):
                        return parsed
                    return [str(parsed)]
                except (ValueError, SyntaxError):
                    if "," in v:
                        return [item.strip() for item in v.split(",") if item.strip()]
                    return [v]
        return ["*"]
    
    # ─── DATABASE ──────────────────────────────────────────────────────
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Database connection URL"
    )
    
    DB_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Database connection pool overflow")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Database connection pool timeout")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries")
    
    # ─── SUPABASE ──────────────────────────────────────────────────────
    SUPABASE_URL: Optional[str] = Field(
        default=None,
        description="Supabase project URL"
    )
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(
        default=None,
        description="Supabase service role key"
    )
    SUPABASE_JWT_SECRET: Optional[str] = Field(
        default=None,
        description="Supabase JWT secret"
    )
    SUPABASE_ANON_KEY: Optional[str] = Field(
        default=None,
        description="Supabase anonymous key"
    )
    
    # ─── JWT AUTHENTICATION ────────────────────────────────────────────
    JWT_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="JWT secret key"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiry")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiry")
    
    # ─── REDIS / CACHING ──────────────────────────────────────────────
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL"
    )
    CACHE_TTL_SECONDS: int = Field(default=300, description="Default cache TTL")
    
    # ─── EMAIL ──────────────────────────────────────────────────────────
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_FROM_EMAIL: Optional[str] = Field(default=None, description="Sender email address")
    SMTP_FROM_NAME: str = Field(default="AUTO-V", description="Sender display name")
    SMTP_USE_TLS: bool = Field(default=True, description="Use TLS for SMTP")
    SMTP_USE_SSL: bool = Field(default=False, description="Use SSL for SMTP")
    
    # ─── RATE LIMITING ──────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Rate limit per minute")
    RATE_LIMIT_PER_DAY: int = Field(default=1000, description="Rate limit per day")
    ENABLE_RATE_LIMITING: bool = Field(default=True, description="Enable rate limiting")
    
    # ─── FILE UPLOAD ──────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, description="Maximum file upload size")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["jpg", "jpeg", "png", "pdf", "doc", "docx"],
        description="Allowed file extensions"
    )
    UPLOAD_DIR: str = Field(default="./uploads", description="Upload directory path")
    
    # ─── LOGGING ──────────────────────────────────────────────────────
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    # ─── FEATURE FLAGS ──────────────────────────────────────────────────
    ENABLE_SWAGGER: bool = Field(default=True, description="Enable Swagger documentation")
    ENABLE_EMAIL: bool = Field(default=True, description="Enable email sending")
    ENABLE_CACHING: bool = Field(default=True, description="Enable Redis caching")
    
    # ─── PYDANTIC CONFIGURATION ──────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # ─── VALIDATION METHODS ──────────────────────────────────────────
    def is_development(self) -> bool:
        return self.ENV.lower() in ["dev", "development", "local"]
    
    def is_production(self) -> bool:
        return self.ENV.lower() in ["prod", "production"]
    
    def is_staging(self) -> bool:
        return self.ENV.lower() in ["stage", "staging"]
    
    def database_configured(self) -> bool:
        return self.DATABASE_URL is not None and self.DATABASE_URL != ""
    
    def supabase_configured(self) -> bool:
        return (
            self.SUPABASE_URL is not None and self.SUPABASE_URL != "" and
            self.SUPABASE_SERVICE_ROLE_KEY is not None and self.SUPABASE_SERVICE_ROLE_KEY != ""
        )
    
    def redis_configured(self) -> bool:
        return self.REDIS_URL is not None and self.REDIS_URL != ""


settings = Settings()
