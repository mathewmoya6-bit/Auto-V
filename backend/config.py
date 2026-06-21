# backend/config.py
import os
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Production Configuration"""
    
    # ─── SUPABASE ──────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE: str = os.getenv("SUPABASE_SERVICE_ROLE", "")
    
    # ─── APIs ──────────────────────────────────────────────
    CARAPI_KEY: str = os.getenv("CARAPI_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_VISION_API_KEY: str = os.getenv("GOOGLE_VISION_API_KEY", "")
    
    # ─── M-Pesa ────────────────────────────────────────────
    MPESA_CONSUMER_KEY: str = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET: str = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE: str = os.getenv("MPESA_SHORTCODE", "174379")
    MPESA_PASSKEY: str = os.getenv("MPESA_PASSKEY", "")
    MPESA_CALLBACK_URL: str = os.getenv("MPESA_CALLBACK_URL", "")
    MPESA_ENVIRONMENT: str = os.getenv("MPESA_ENVIRONMENT", "production")
    
    # ─── JWT ──────────────────────────────────────────────
    JWT_SECRET: str = os.getenv("JWT_SECRET", "auto-v-production-secret-key-2024")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # ─── App ──────────────────────────────────────────────
    APP_NAME: str = os.getenv("APP_NAME", "AUTO-V Professional Valuation Engine")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", 8000))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # ─── CORS ──────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "https://auto-v.meipressgroup.com,https://www.auto-v.meipressgroup.com"
    ).split(",")
    
    # ─── Redis ─────────────────────────────────────────────
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://redis:6379")
    REDIS_TTL: int = int(os.getenv("REDIS_TTL", 3600))
    
    # ─── AI ──────────────────────────────────────────────
    AI_WEIGHT: float = float(os.getenv("AI_WEIGHT", 0.4))
    AI_MIN_CONFIDENCE: float = float(os.getenv("AI_MIN_CONFIDENCE", 0.3))
    AI_CACHE_ENABLED: bool = os.getenv("AI_CACHE_ENABLED", "true").lower() == "true"
    AI_FALLBACK_ENABLED: bool = os.getenv("AI_FALLBACK_ENABLED", "true").lower() == "true"
    
    # ─── Features ──────────────────────────────────────────
    FEATURE_MPESA: bool = os.getenv("FEATURE_MPESA", "true").lower() == "true"
    FEATURE_VIN_AUTOFILL: bool = os.getenv("FEATURE_VIN_AUTOFILL", "true").lower() == "true"
    FEATURE_AI_VALUATION: bool = os.getenv("FEATURE_AI_VALUATION", "true").lower() == "true"
    FEATURE_FRAUD_DETECTION: bool = os.getenv("FEATURE_FRAUD_DETECTION", "true").lower() == "true"
    FEATURE_DOCUMENT_VERIFICATION: bool = os.getenv("FEATURE_DOCUMENT_VERIFICATION", "true").lower() == "true"
    
    # ─── Rate Limiting ─────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", 60))
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))
    IP_RATE_LIMIT: int = int(os.getenv("IP_RATE_LIMIT", 100))
    
    # ─── File Uploads ──────────────────────────────────────
    MAX_IMAGE_SIZE: int = int(os.getenv("MAX_IMAGE_SIZE", 10485760))
    MAX_DOCUMENT_SIZE: int = int(os.getenv("MAX_DOCUMENT_SIZE", 20971520))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/uploads/temp")
    
    # ─── Logging ───────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "WARNING")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required = [
            ("SUPABASE_URL", cls.SUPABASE_URL),
            ("SUPABASE_ANON_KEY", cls.SUPABASE_ANON_KEY),
            ("CARAPI_KEY", cls.CARAPI_KEY),
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
        ]
        
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True

config = Config()
