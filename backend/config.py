"""
AUTO-V Core Configuration
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "AUTO-V"
    APP_VERSION: str = "2.0.0"
    ENV: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # M-Pesa
    MPESA_CONSUMER_KEY: str
    MPESA_CONSUMER_SECRET: str
    MPESA_PASSKEY: str
    MPESA_SHORTCODE: str = "4095377"
    MPESA_ENVIRONMENT: str = "sandbox"
    MPESA_CALLBACK_URL: str = "https://auto-v.onrender.com/api/mpesa/callback"
    BASE_URL: str = "https://auto-v.onrender.com"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "https://auto-v.meipressgroup.com",
        "https://www.auto-v.meipressgroup.com",
        "https://auto-v.onrender.com",
        "http://localhost:3000",
        "http://localhost:5173"
    ]
    
    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
