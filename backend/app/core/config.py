# app/core/config.py
# =============================================================================
# AUTO-V API - Settings
# =============================================================================

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Supabase Postgres connection string, e.g.
    # postgresql://postgres:<password>@<host>:5432/postgres
    # or the pgbouncer/transaction-pooler URL Supabase gives you.
    DATABASE_URL: str = ""

    DEBUG: bool = False

    # JSON array in the env, e.g. CORS_ORIGINS=["https://auto-v.meipressgroup.com"]
    CORS_ORIGINS: list[str] = ["*"]

    # This app's real deployment has many more env vars than this minimal
    # settings module declares (payment/webhook retry config, db pool sizing,
    # session/cookie flags, maintenance mode, etc). Rather than redeclare
    # every field here and risk drifting from the real app again, ignore
    # anything this module doesn't explicitly care about instead of
    # crashing the whole process on startup.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def database_configured(self) -> bool:
        return bool(self.DATABASE_URL)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
