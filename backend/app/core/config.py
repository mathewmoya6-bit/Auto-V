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

    CORS_ORIGINS: List[str] = Field(
        default=[
            "https://auto-v.meipressgroup.com",
            "https://www.auto-v.meipressgroup.com",
            "https://auto-v.onrender.com",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5500",
        ]
    )

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

    # Database configuration
    DATABASE_URL: Optional[str] = Field(
        default="postgresql+asyncpg://postgres.tsvejnzxrxrrecgquxbq:aDANGI22313261@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?ssl=require"
    )
    DB_POOL_SIZE: int = Field(default=10)
    DB_MAX_OVERFLOW: int = Field(default=20)
    DB_POOL_TIMEOUT: int = Field(default=30)

    JWT_SECRET_KEY: str = Field(default="CHANGE-ME-INSECURE-DEFAULT-SECRET")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24)

    ENABLE_SWAGGER: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore",
    )

    def database_configured(self) -> bool:
        return bool(self.DATABASE_URL)


settings = Settings()
