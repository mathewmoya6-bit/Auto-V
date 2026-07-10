from pydantic_settings import BaseSettings
from typing import Optional, List
import json


class Settings(BaseSettings):
    # ============================================================
    # APP SETTINGS
    # ============================================================
    app_name: str = "AUTO-V Professional Valuation Engine"
    app_version: str = "2.0.0"
    env: str = "production"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 10000
    api_v1_prefix: str = "/api/v1"
    project_name: str = "AUTO-V API"
    
    # ============================================================
    # DATABASE (Supabase PostgreSQL)
    # ============================================================
    database_url: Optional[str] = None
    
    # ============================================================
    # SUPABASE
    # ============================================================
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: Optional[str] = None
    
    # ============================================================
    # SECURITY
    # ============================================================
    secret_key: str
    jwt_secret: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    refresh_token_expire_days: int = 30
    
    # ============================================================
    # CORS
    # ============================================================
    cors_origins: List[str] = ["*"]
    allowed_hosts: List[str] = []
    
    # ============================================================
    # REDIS
    # ============================================================
    redis_enabled: bool = False
    redis_url: Optional[str] = None
    redis_max_connections: int = 10
    redis_ttl: int = 3600
    
    # ============================================================
    # RATE LIMITING
    # ============================================================
    ratelimit_enabled: bool = False
    ratelimit_default: str = "100/minute"
    ratelimit_storage_uri: Optional[str] = None
    max_login_attempts: int = 5
    ip_rate_limit: int = 100
    
    # ============================================================
    # LOGGING
    # ============================================================
    log_level: str = "INFO"
    log_format: str = "json"
    
    # ============================================================
    # AI SERVICES
    # ============================================================
    ai_weight: float = 0.4
    ai_min_confidence: float = 0.3
    ai_cache_enabled: bool = True
    ai_fallback_enabled: bool = True
    ai_predictions_enabled: bool = True
    ai_cache_ttl: int = 3600
    
    # ============================================================
    # FEATURES
    # ============================================================
    feature_mpesa: bool = False
    feature_vin_autofill: bool = False
    feature_ai_valuation: bool = False
    feature_fraud_detection: bool = False
    feature_document_verification: bool = False
    feature_report_generation: bool = False
    feature_qr_verification: bool = False
    enable_image_analysis: bool = False
    enable_document_ocr: bool = False
    enable_price_prediction: bool = False
    enable_chat_assistant: bool = False
    realtime_enabled: bool = False
    
    # ============================================================
    # STORAGE
    # ============================================================
    storage_type: str = "supabase"
    storage_bucket: str = "autov-storage"
    max_image_size: int = 10485760
    max_document_size: int = 20971520
    
    # ============================================================
    # VEHICLE DATA API
    # ============================================================
    carapi_key: Optional[str] = None
    
    # ============================================================
    # EXTERNAL API KEYS
    # ============================================================
    openai_api_key: Optional[str] = None
    google_vision_api_key: Optional[str] = None
    
    # ============================================================
    # EMAIL
    # ============================================================
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_tls: bool = True
    
    # ============================================================
    # REALTIME
    # ============================================================
    realtime_heartbeat_interval: int = 30
    realtime_retry_attempts: int = 3
    realtime_retry_delay: int = 2
    realtime_max_channels: int = 100
    
    # ============================================================
    # PAYMENT WORKER
    # ============================================================
    payment_worker_enabled: bool = False
    payment_worker_interval: int = 60
    payment_retry_max: int = 3
    payment_retry_delay: int = 60
    
    # ============================================================
    # WEBHOOKS
    # ============================================================
    webhook_retry_max: int = 3
    webhook_retry_delay: int = 30
    webhook_timeout: int = 30
    
    # ============================================================
    # DATABASE POOL
    # ============================================================
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    
    # ============================================================
    # SESSION
    # ============================================================
    session_timeout_minutes: int = 60
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    
    # ============================================================
    # SSL
    # ============================================================
    ssl_enabled: bool = False
    
    # ============================================================
    # MAINTENANCE
    # ============================================================
    maintenance_mode: bool = False
    maintenance_message: str = "System is currently undergoing maintenance. Please try again later."
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            """Parse environment variables with special handling for specific types"""
            # Handle boolean values
            if raw_val.lower() in ("true", "false"):
                return raw_val.lower() == "true"
            
            # Handle CORS_ORIGINS and ALLOWED_HOSTS (JSON arrays)
            if field_name in ("cors_origins", "allowed_hosts"):
                try:
                    return json.loads(raw_val)
                except:
                    return [item.strip() for item in raw_val.split(",")]
            
            # Handle integer values for known integer fields
            if field_name in (
                "port", "access_token_expire_minutes", "refresh_token_expire_days",
                "redis_max_connections", "redis_ttl", "max_login_attempts",
                "ip_rate_limit", "ai_cache_ttl", "max_image_size", "max_document_size",
                "realtime_heartbeat_interval", "realtime_retry_attempts", 
                "realtime_retry_delay", "realtime_max_channels", "payment_worker_interval",
                "payment_retry_max", "payment_retry_delay", "webhook_retry_max",
                "webhook_retry_delay", "webhook_timeout", "db_pool_size",
                "db_max_overflow", "db_pool_timeout", "session_timeout_minutes",
                "ai_weight", "ai_min_confidence"
            ):
                try:
                    return int(raw_val)
                except ValueError:
                    return raw_val
            
            # Handle float values
            if field_name in ("ai_weight", "ai_min_confidence"):
                try:
                    return float(raw_val)
                except ValueError:
                    return raw_val
            
            return raw_val


settings = Settings()
