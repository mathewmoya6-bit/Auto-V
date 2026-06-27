# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import field_validator
import json

class Settings(BaseSettings):
    # App
    APP_NAME: str = "AUTO-V Professional Valuation Engine"
    APP_VERSION: str = "2.0.0"
    ENV: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 10000
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "AUTO-V API"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12
    
    # M-PESA
    MPESA_CONSUMER_KEY: str
    MPESA_CONSUMER_SECRET: str
    MPESA_SHORTCODE: str
    MPESA_PASSKEY: str
    MPESA_ENVIRONMENT: str = "production"
    BASE_URL: str
    MPESA_CALLBACK_URL: str
    
    # CORS - JSON arrays
    CORS_ORIGINS: List[str] = [
        "https://auto-v.meipressgroup.com",
        "https://www.auto-v.meipressgroup.com",
        "https://auto-v.onrender.com",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5500"
    ]
    ALLOWED_HOSTS: List[str] = [
        "auto-v.meipressgroup.com",
        "www.auto-v.meipressgroup.com",
        "auto-v.onrender.com",
        "localhost",
        "127.0.0.1"
    ]
    
    # Redis
    REDIS_ENABLED: bool = True
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_TTL: int = 3600
    
    # Rate Limiting
    RATELIMIT_ENABLED: bool = True
    RATELIMIT_DEFAULT: str = "100/minute"
    RATELIMIT_STORAGE_URI: str
    MAX_LOGIN_ATTEMPTS: int = 5
    IP_RATE_LIMIT: int = 100
    
    # Logging
    LOG_LEVEL: str = "INFO"
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
    MAX_IMAGE_SIZE: int = 10485760
    MAX_DOCUMENT_SIZE: int = 20971520
    STORAGE_TYPE: str = "supabase"
    STORAGE_BUCKET: str = "autov-storage"
    
    # Vehicle Data API
    CARAPI_KEY: str
    
    # External API Keys
    OPENAI_API_KEY: str
    GOOGLE_VISION_API_KEY: str
    
    # SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_TLS: bool = True
    
    # Realtime
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
    
    # Database Pool
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    
    # Session
    SESSION_TIMEOUT_MINUTES: int = 60
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    
    # SSL/TLS
    SSL_ENABLED: bool = False
    
    # Maintenance
    MAINTENANCE_MODE: bool = False
    MAINTENANCE_MESSAGE: str = "System is currently undergoing maintenance. Please try again later."
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def validate_cors_origins(cls, v):
        """Parse CORS_ORIGINS from JSON string or comma-separated string"""
        if isinstance(v, str):
            try:
                # Try to parse as JSON
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                # If not JSON, split by comma
                return [x.strip() for x in v.split(',') if x.strip()]
        return v
    
    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def validate_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from JSON string or comma-separated string"""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [x.strip() for x in v.split(',') if x.strip()]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

# Create settings instance
settings = Settings()
