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
    # SUPABASE - Required
    # ============================================================
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    
    # ============================================================
    # SECURITY - Required
    # ============================================================
    secret_key: str
    jwt_secret: str
    algorithm: str = "HS256"
    
    # ============================================================
    # CORS - Required
    # ============================================================
    cors_origins: List[str] = ["*"]
    
    # ============================================================
    # OPTIONAL - M-Pesa
    # ============================================================
    mpesa_consumer_key: Optional[str] = None
    mpesa_consumer_secret: Optional[str] = None
    mpesa_passkey: Optional[str] = None
    mpesa_shortcode: Optional[str] = None
    mpesa_environment: str = "sandbox"
    
    # ============================================================
    # OPTIONAL - Logging
    # ============================================================
    log_level: str = "INFO"
    log_format: str = "text"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            """Parse special field types"""
            if field_name == "cors_origins":
                try:
                    return json.loads(raw_val)
                except:
                    return [origin.strip() for origin in raw_val.split(",")]
            
            # Parse boolean values
            if raw_val.lower() in ("true", "false"):
                return raw_val.lower() == "true"
            
            # Parse integer values
            if field_name in ("port",):
                try:
                    return int(raw_val)
                except ValueError:
                    return raw_val
            
            return raw_val


settings = Settings()
