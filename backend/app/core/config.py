# app/core/config.py
# =============================================================================
# AUTO-V API - Settings
# =============================================================================

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase Postgres connection string, e.g.
    # postgresql://postgres:<password>@<host>:5432/postgres
    # or the pgbouncer/transaction-pooler URL Supabase gives you.
    DATABASE_URL: str = ""

    DEBUG: bool = False

    # Comma-separated in the env, e.g. CORS_ORIGINS=https://auto-v.meipressgroup.com
    CORS_ORIGINS: list[str] = ["*"]

    def database_configured(self) -> bool:
        return bool(self.DATABASE_URL)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
