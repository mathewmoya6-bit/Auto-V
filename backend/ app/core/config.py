# app/core/config.py (COMPLETE UPDATED VERSION)
from pydantic_settings import BaseSettings
from typing import List, Optional, Union
import os
from pathlib import Path
from pydantic import field_validator, Field

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
    SUPABASE_URL: str = "https://tsvejnzxrxrrecgquxbq.supabase.co"
    SUPABASE_ANON_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ"
    SUPABASE_SERVICE_ROLE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTE4NzM2OCwiZXhwIjoyMDk2NzYzMzY4fQ.your_service_role_key_here"
    SUPABASE_JWT_SECRET: str = "your_jwt_secret_here"
    SUPABASE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzdmVqbnp4cnhycmVjZ3F1eGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExODczNjgsImV4cCI6MjA5Njc2MzM2OH0.PCEppwafuPatBoWh4OnhzgHv6fA9uF5-bWW9mmf2VoQ"
    
    # Security
    SECRET_KEY: str = "b7c973b0-931c-4fb8-82b0-d93827cfdee8"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12
    JWT_SECRET: str = "b7c973b0-931c-4fb8-82b0-d93827cfdee8"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # M-PESA
    MPESA_CONSUMER_KEY: str = "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv"
    MPESA_CONSUMER_SECRET: str = "aGGo8AuPJVpsZLcs"
    MPESA_SHORTCODE: str = "4095377"
    MPESA_PASSKEY: str = "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277"
    MPESA_CALLBACK_URL: str = "https://auto-v.onrender.com/api/webhooks/mpesa"
    MPESA_ENVIRONMENT: str = "production"
    MPESA_ENV: str = "production"
    BASE_URL: str = "https://auto-v.onrender.com"
    
    # CORS - Stored as string, parsed to list via validator
    CORS_ORIGINS: str = "https://auto-v.meipressgroup.com,https://www.auto-v.meipressgroup.com,http://localhost:3000,http://localhost:5500,http://localhost:5173,https://auto-v.onrender.com"
    ALLOWED_HOSTS: str = "auto-v.meipressgroup.com,www.auto-v.meipressgroup.com,localhost,127.0.0.1,auto-v.onrender.com"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_ENABLED: bool = True
    REDIS_TTL: int = 3600
    
    # Rate Limiting
    RATELIMIT_ENABLED: bool = True
    RATELIMIT_DEFAULT: str = "100/minute"
    RATELIMIT_STORAGE_URI: str = "redis://redis:6379"
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
    CARAPI_KEY: str = "carapi_45747df211066bb9d14224ae998de7e7"
    
    # External API Keys
    OPENAI_API_KEY: str = "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"
    GOOGLE_VISION_API_KEY: str = "AIzaSyC8pJt4X8nV5jQ2nX9rL3mW6kY8tH4vB2c"
    
    # SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "noreply@autov.africa"
    SMTP_PASSWORD: str = "your_smtp_password_here"
    SMTP_FROM_EMAIL: str = "noreply@autov.africa"
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
    SSL_ENABLED: bool = True
    SSL_CERT_PATH: str = "/etc/ssl/certs/autov.crt"
    SSL_KEY_PATH: str = "/etc/ssl/private/autov.key"
    
    # Maintenance
    MAINTENANCE_MODE: bool = False
    MAINTENANCE_MESSAGE: str = "System is currently undergoing maintenance. Please try again later."
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from string to list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from string to list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(',') if host.strip()]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env

# Create settings instance
settings = Settings()

# For backwards compatibility, expose the parsed values
settings.CORS_ORIGINS_LIST = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else []
settings.ALLOWED_HOSTS_LIST = settings.ALLOWED_HOSTS if isinstance(settings.ALLOWED_HOSTS, list) else []
