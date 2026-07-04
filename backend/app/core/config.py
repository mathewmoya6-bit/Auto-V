# app/core/config.py
# =============================================================================
# AUTO-V API - Configuration Settings
# =============================================================================

import json
import ast
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field


class Settings(BaseSettings):
    APP_NAME: str = "AUTO-V API"
    APP_VERSION: str = "1.0.0"
    ENV: str = Field(default="production")
    DEBUG: bool = Field(default=False)

    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    LOG_LEVEL: str = Field(default="info")

    API_V1_PREFIX: str = Field(default="/api/v1")

    # ─── CORS Configuration ──────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(
        default=[
            "https://auto-v.meipressgroup.com",
            "https://www.auto-v.meipressgroup.com",
            "https://auto-v.onrender.com",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    )

    CORS_ADDITIONAL_ORIGINS: Optional[str] = Field(default=None)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return ["*"]
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [str(parsed)]
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(v)
                    return parsed if isinstance(parsed, list) else [str(parsed)]
                except (ValueError, SyntaxError):
                    if "," in v:
                        return [item.strip() for item in v.split(",") if item.strip()]
                    return [v]
        return ["*"]

    def get_cors_origins(self) -> List[str]:
        """Get all CORS origins including additional ones from environment."""
        origins = list(self.CORS_ORIGINS)
        if self.CORS_ADDITIONAL_ORIGINS:
            try:
                additional = json.loads(self.CORS_ADDITIONAL_ORIGINS)
                if isinstance(additional, list):
                    origins.extend(additional)
            except json.JSONDecodeError:
                if "," in self.CORS_ADDITIONAL_ORIGINS:
                    origins.extend([o.strip() for o in self.CORS_ADDITIONAL_ORIGINS.split(",") if o.strip()])
                else:
                    origins.append(self.CORS_ADDITIONAL_ORIGINS.strip())
        return list(set(origins))

    # ─── Database Configuration ──────────────────────────────────────
    # IMPORTANT: never hardcode a real connection string / password here
    # as a "default" — this file is committed to git. Set DATABASE_URL
    # as an env var on Render. If unset, the app fails loudly at startup
    # (see the RuntimeError check in app/core/database.py) instead of
    # silently falling back to a real, potentially leaked credential.
    DATABASE_URL: Optional[str] = Field(default=None)
    DB_POOL_SIZE: int = Field(default=10)
    DB_MAX_OVERFLOW: int = Field(default=20)
    DB_POOL_TIMEOUT: int = Field(default=30)
    DB_POOL_PRE_PING: bool = Field(default=True)
    DB_POOL_RECYCLE: int = Field(default=300)

    # ─── Security Configuration ──────────────────────────────────────
    # IMPORTANT: set a real JWT_SECRET_KEY as a Render env var.
    # Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
    JWT_SECRET_KEY: str = Field(default="CHANGE-ME-INSECURE-DEFAULT-SECRET")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)

    # ─── SSL/HTTPS Configuration ──────────────────────────────────────
    # Render handles SSL termination for incoming traffic; these are
    # only relevant for local uvicorn dev with SSL enabled directly.
    SSL_ENABLED: bool = Field(default=False)
    SSL_KEYFILE: Optional[str] = Field(default=None)
    SSL_CERTFILE: Optional[str] = Field(default=None)

    # ─── API Configuration ───────────────────────────────────────────
    ENABLE_SWAGGER: bool = Field(default=True)
    API_RATE_LIMIT: int = Field(default=100)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def database_configured(self) -> bool:
        return bool(self.DATABASE_URL)

    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    def is_development(self) -> bool:
        return self.ENV.lower() in ["development", "dev", "local"]


settings = Settings()
