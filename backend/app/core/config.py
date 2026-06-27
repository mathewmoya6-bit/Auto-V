"""
AUTO-V Core Configuration - FastAPI Version
"""

import os
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "AUTO-V Professional Valuation Engine"
    APP_VERSION: str = "2.0.0"
    ENV: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 10000
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "AUTO-V API"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12
    
    # M-Pesa
    MPESA_CONSUMER_KEY: str
    MPESA_CONSUMER_SECRET: str
    MPESA_PASSKEY: str
    MPESA_SHORTCODE: str = "4095377"
    MPESA_ENVIRONMENT: str = "production"
    MPESA_CALLBACK_URL: str = "https://auto-v.meipressgroup.com/api/webhooks/mpesa"
    BASE_URL: str = "https://auto-v.meipressgroup.com"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "https://auto-v.meipressgroup.com",
        "https://www.auto-v.meipressgroup.com",
        "http://localhost:3000",
        "http://localhost:5500"
    ]
    ALLOWED_HOSTS: List[str] = [
        "auto-v.meipressgroup.com",
        "www.auto-v.meipressgroup.com",
        "localhost",
        "127.0.0.1"
    ]
    
    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_ENABLED: bool = True
    
    # Rate Limiting
    RATELIMIT_ENABLED: bool = True
    RATELIMIT_DEFAULT: str = "100/minute"
    RATELIMIT_STORAGE_URI: str = "redis://redis:6379"
    MAX_LOGIN_ATTEMPTS: int = 5
    IP_RATE_LIMIT: int = 100
    
    # Logging
    LOG_LEVEL: str = "WARNING"
    LOG_FILE: str = "logs/app.log"
    LOG_FORMAT: str = "json"
    LOG_DIR: str = "logs"
    
    # AI Services
    AI_WEIGHT: float = 0.4
    AI_MIN_CONFIDENCE: float = 0.3
    AI_CACHE_ENABLED: bool = True
    AI_FALLBACK_ENABLED: bool = True
    AI_MODEL_PATH: str = "./models"
    AI_PREDICTIONS_ENABLED: bool = True
    AI_CACHE_TTL: int = 3600
    
    # Feature Flags
    FEATURE_MPESA: bool = True
    FEATURE_VIN_AUTOFILL: bool = True
    FEATURE_AI_VALUATION: bool = True
    FEATURE_FRAUD_DETECTION: bool = True
    FEATURE_DOCUMENT_VERIFICATION: bool = True
    FEATURE_REPORT_GENERATION: bool = True
    FEATURE_QR_VERIFICATION: bool = True
    ENABLE_IMAGE_ANALYSIS: bool = True
    ENABLE_DOCUMENT_OCR: bool = True
    ENABLE_PRICE_PREDICTION: bool = True
    ENABLE_CHAT_ASSISTANT: bool = True
    REALTIME_ENABLED: bool = True
    
    # File Uploads
    MAX_IMAGE_SIZE: int = 10485760   # 10MB
    MAX_DOCUMENT_SIZE: int = 20971520  # 20MB
    STORAGE_TYPE: str = "supabase"
    STORAGE_BUCKET: str = "autov-storage"
    
    # Vehicle API
    CARAPI_KEY: str
    
    # External APIs
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_VISION_API_KEY: Optional[str] = None
    
    # SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@autov.africa"
    SMTP_TLS: bool = True
    
    # Realtime
    REALTIME_ENABLED: bool = True
    REALTIME_HEARTBEAT_INTERVAL: int = 30
    REALTIME_RETRY_ATTEMPTS: int = 3
    REALTIME_RETRY_DELAY: int = 2
    REALTIME_MAX_CHANNELS: int = 100
    
    # Payment Worker
    PAYMENT_WORKER_ENABLED: bool = True
    PAYMENT_WORKER_INTERVAL: int = 60
    PAYMENT_RETRY_MAX: int = 3
    PAYMENT_RETRY_DELAY: int = 60
    
    # Webhooks
    WEBHOOK_RETRY_MAX: int = 3
    WEBHOOK_RETRY_DELAY: int = 30
    WEBHOOK_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
