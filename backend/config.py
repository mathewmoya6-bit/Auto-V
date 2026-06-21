# config.py - AUTO-V Production Configuration
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """
    Production configuration for AUTO-V application.
    All settings are loaded from environment variables.
    """
    
    # ─── APP ──────────────────────────────────────────────────────
    APP_NAME = os.getenv('APP_NAME', 'AUTO-V API')
    APP_VERSION = os.getenv('APP_VERSION', '2.0.0')
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('PORT', 10000))
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    
    # ─── SUPABASE ──────────────────────────────────────────────────
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
    SUPABASE_SERVICE_ROLE = os.getenv('SUPABASE_SERVICE_ROLE', '')
    
    # ─── M-PESA ────────────────────────────────────────────────────
    MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', 'LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv')
    MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', 'aGGo8AuPJVpsZLcs')
    MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277')
    MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '4095377')
    MPESA_SHORTCODE_TYPE = os.getenv('MPESA_SHORTCODE_TYPE', 'paybill')
    MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://auto-v-backend.onrender.com/api/mpesa/callback')
    MPESA_ENV = os.getenv('MPESA_ENV', 'production')
    MPESA_API_URL = 'https://api.safaricom.co.ke' if MPESA_ENV == 'production' else 'https://sandbox.safaricom.co.ke'
    
    # ─── OPENAI ────────────────────────────────────────────────────
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # ─── CARAPI ────────────────────────────────────────────────────
    CARAPI_KEY = os.getenv('CARAPI_KEY', '')
    
    # ─── CORS ──────────────────────────────────────────────────────
    ALLOWED_ORIGINS = os.getenv(
        'ALLOWED_ORIGINS',
        'https://auto-v.meipressgroup.com,https://auto-v.onrender.com,https://auto-v-backend.onrender.com,http://localhost:3000,http://localhost:5000'
    ).split(',')
    
    # ─── JWT ──────────────────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(24).hex())
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days
    
    # ─── REDIS ────────────────────────────────────────────────────
    REDIS_URL = os.getenv('REDIS_URL', '')
    REDIS_TTL = int(os.getenv('REDIS_TTL', 3600))
    
    # ─── RATE LIMITING ────────────────────────────────────────────
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'true').lower() == 'true'
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '100 per hour')
    RATELIMIT_STORAGE_URL = REDIS_URL if REDIS_URL else 'memory://'
    
    # ─── LOGGING ──────────────────────────────────────────────────
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'text')
    
    # ─── FILE UPLOADS ─────────────────────────────────────────────
    MAX_IMAGE_SIZE = int(os.getenv('MAX_IMAGE_SIZE', 10485760))  # 10MB
    MAX_DOCUMENT_SIZE = int(os.getenv('MAX_DOCUMENT_SIZE', 20971520))  # 20MB
    UPLOAD_DIR = os.getenv('UPLOAD_DIR', 'uploads/temp')
    ALLOWED_IMAGE_TYPES = os.getenv('ALLOWED_IMAGE_TYPES', 'image/jpeg,image/png,image/webp,image/heic').split(',')
    ALLOWED_DOCUMENT_TYPES = os.getenv('ALLOWED_DOCUMENT_TYPES', 'application/pdf,image/jpeg,image/png').split(',')
    
    # ─── AI ──────────────────────────────────────────────────────
    AI_WEIGHT = float(os.getenv('AI_WEIGHT', 0.4))
    AI_MIN_CONFIDENCE = float(os.getenv('AI_MIN_CONFIDENCE', 0.3))
    AI_CACHE_ENABLED = os.getenv('AI_CACHE_ENABLED', 'true').lower() == 'true'
    AI_FALLBACK_ENABLED = os.getenv('AI_FALLBACK_ENABLED', 'true').lower() == 'true'
    
    # ─── FEATURES ──────────────────────────────────────────────────
    FEATURE_MPESA = os.getenv('FEATURE_MPESA', 'true').lower() == 'true'
    FEATURE_VIN_AUTOFILL = os.getenv('FEATURE_VIN_AUTOFILL', 'true').lower() == 'true'
    FEATURE_AI_VALUATION = os.getenv('FEATURE_AI_VALUATION', 'true').lower() == 'true'
    FEATURE_FRAUD_DETECTION = os.getenv('FEATURE_FRAUD_DETECTION', 'true').lower() == 'true'
    FEATURE_DOCUMENT_VERIFICATION = os.getenv('FEATURE_DOCUMENT_VERIFICATION', 'true').lower() == 'true'
    FEATURE_REPORT_GENERATION = os.getenv('FEATURE_REPORT_GENERATION', 'true').lower() == 'true'
    FEATURE_QR_VERIFICATION = os.getenv('FEATURE_QR_VERIFICATION', 'true').lower() == 'true'
    ENABLE_IMAGE_ANALYSIS = os.getenv('ENABLE_IMAGE_ANALYSIS', 'true').lower() == 'true'
    ENABLE_DOCUMENT_OCR = os.getenv('ENABLE_DOCUMENT_OCR', 'true').lower() == 'true'
    ENABLE_PRICE_PREDICTION = os.getenv('ENABLE_PRICE_PREDICTION', 'true').lower() == 'true'
    ENABLE_CHAT_ASSISTANT = os.getenv('ENABLE_CHAT_ASSISTANT', 'true').lower() == 'true'
    
    # ─── SESSION ────────────────────────────────────────────────────
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 3600))
    REFRESH_TIMEOUT = int(os.getenv('REFRESH_TIMEOUT', 604800))
    
    # ─── SECURITY ──────────────────────────────────────────────────
    SECURE_COOKIES = os.getenv('SECURE_COOKIES', 'true').lower() == 'true'
    SESSION_COOKIE_SECURE = SECURE_COOKIES
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # ─── DATABASE ──────────────────────────────────────────────────
    # Using Supabase as primary database
    
    # ─── EMAIL ─────────────────────────────────────────────────────
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_FROM = os.getenv('SMTP_FROM', 'noreply@auto-v.meipressgroup.com')
    
    # ─── WEBHOOKS ──────────────────────────────────────────────────
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate all required configuration.
        
        Returns:
            bool: True if valid, False otherwise
        """
        errors = []
        warnings = []
        
        # ─── Validate Supabase ──────────────────────────────────
        if not cls.SUPABASE_URL:
            errors.append("SUPABASE_URL is not set")
        elif not cls.SUPABASE_URL.startswith('https://'):
            errors.append("SUPABASE_URL must use HTTPS")
        
        if not cls.SUPABASE_ANON_KEY:
            errors.append("SUPABASE_ANON_KEY is not set")
        elif len(cls.SUPABASE_ANON_KEY) < 50:
            warnings.append("SUPABASE_ANON_KEY seems too short")
        
        # ─── Validate M-Pesa ──────────────────────────────────
        if not cls.MPESA_CONSUMER_KEY:
            warnings.append("MPESA_CONSUMER_KEY is not set")
        if not cls.MPESA_CONSUMER_SECRET:
            warnings.append("MPESA_CONSUMER_SECRET is not set")
        if not cls.MPESA_PASSKEY:
            warnings.append("MPESA_PASSKEY is not set")
        if not cls.MPESA_CALLBACK_URL:
            warnings.append("MPESA_CALLBACK_URL is not set")
        
        if cls.MPESA_CALLBACK_URL and not cls.MPESA_CALLBACK_URL.startswith('https://'):
            errors.append("MPESA_CALLBACK_URL must use HTTPS in production")
        
        if cls.MPESA_SHORTCODE and not cls.MPESA_SHORTCODE.isdigit():
            errors.append(f"MPESA_SHORTCODE must be numeric: {cls.MPESA_SHORTCODE}")
        
        # ─── Validate Environment ──────────────────────────────
        if cls.ENV == 'production' and cls.DEBUG:
            errors.append("DEBUG should be False in production")
        
        # ─── Validate Security ──────────────────────────────────
        if cls.ENV == 'production' and cls.SECRET_KEY == os.urandom(24).hex():
            warnings.append("SECRET_KEY should be set in environment, not using default")
        
        # ─── Log results ────────────────────────────────────────
        if errors:
            for error in errors:
                import logging
                logging.error(f"❌ Configuration error: {error}")
            return False
        
        if warnings:
            for warning in warnings:
                import logging
                logging.warning(f"⚠️ Configuration warning: {warning}")
        
        return True
    
    @classmethod
    def get_summary(cls) -> dict:
        """
        Get configuration summary.
        
        Returns:
            dict: Configuration summary
        """
        return {
            'app_name': cls.APP_NAME,
            'version': cls.APP_VERSION,
            'environment': cls.ENV,
            'debug': cls.DEBUG,
            'port': cls.PORT,
            'supabase_url': cls.SUPABASE_URL,
            'mpesa_shortcode': cls.MPESA_SHORTCODE,
            'mpesa_environment': cls.MPESA_ENV,
            'mpesa_callback_url': cls.MPESA_CALLBACK_URL,
            'redis_configured': bool(cls.REDIS_URL),
            'rate_limiting_enabled': cls.RATELIMIT_ENABLED,
            'log_level': cls.LOG_LEVEL,
            'features': {
                'mpesa': cls.FEATURE_MPESA,
                'vin_autofill': cls.FEATURE_VIN_AUTOFILL,
                'ai_valuation': cls.FEATURE_AI_VALUATION,
                'fraud_detection': cls.FEATURE_FRAUD_DETECTION,
                'document_verification': cls.FEATURE_DOCUMENT_VERIFICATION,
                'report_generation': cls.FEATURE_REPORT_GENERATION,
                'qr_verification': cls.FEATURE_QR_VERIFICATION,
            },
            'ai': {
                'weight': cls.AI_WEIGHT,
                'min_confidence': cls.AI_MIN_CONFIDENCE,
                'cache_enabled': cls.AI_CACHE_ENABLED,
                'fallback_enabled': cls.AI_FALLBACK_ENABLED,
            }
        }
    
    @classmethod
    def print_summary(cls):
        """Print configuration summary."""
        import logging
        logger = logging.getLogger(__name__)
        
        summary = cls.get_summary()
        
        logger.info("=" * 60)
        logger.info("📋 Configuration Summary:")
        logger.info(f"  Application: {summary['app_name']} v{summary['version']}")
        logger.info(f"  Environment: {summary['environment']}")
        logger.info(f"  Port: {summary['port']}")
        logger.info(f"  Supabase URL: {summary['supabase_url']}")
        logger.info(f"  M-Pesa Shortcode: {summary['mpesa_shortcode']}")
        logger.info(f"  M-Pesa Environment: {summary['mpesa_environment']}")
        logger.info(f"  Redis: {'✅ Configured' if summary['redis_configured'] else '❌ Not configured'}")
        logger.info(f"  Rate Limiting: {'✅ Enabled' if summary['rate_limiting_enabled'] else '❌ Disabled'}")
        logger.info(f"  Log Level: {summary['log_level']}")
        logger.info("-" * 60)
        logger.info("📌 Features:")
        for key, value in summary['features'].items():
            status = '✅' if value else '❌'
            logger.info(f"    {status} {key.replace('_', ' ').title()}")
        logger.info("-" * 60)
        logger.info("🤖 AI Settings:")
        logger.info(f"    Weight: {summary['ai']['weight']}")
        logger.info(f"    Min Confidence: {summary['ai']['min_confidence']}")
        logger.info(f"    Cache: {'✅' if summary['ai']['cache_enabled'] else '❌'}")
        logger.info(f"    Fallback: {'✅' if summary['ai']['fallback_enabled'] else '❌'}")
        logger.info("=" * 60)

# ─── Create config instance ────────────────────────────────────
config = Config()

# ─── Quick Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Validate config
    if config.validate():
        print("✅ Configuration validated successfully")
        config.print_summary()
    else:
        print("❌ Configuration validation failed")
