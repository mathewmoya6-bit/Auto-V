from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    
    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    
    # CORS
    cors_origins: list[str] = ["*"]
    
    # M-Pesa
    mpesa_consumer_key: Optional[str] = None
    mpesa_consumer_secret: Optional[str] = None
    mpesa_passkey: Optional[str] = None
    mpesa_shortcode: Optional[str] = None
    mpesa_environment: str = "sandbox"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
