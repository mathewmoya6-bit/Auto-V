# app/core/database.py
import os
import logging
from supabase import create_client, Client
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_ANON_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    logger.info("✅ Supabase client initialized")
else:
    logger.warning("⚠️  Supabase credentials not configured")


def get_supabase() -> Optional[Client]:
    return supabase


def get_admin_client() -> Optional[Client]:
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return None


def is_configured() -> bool:
    return supabase is not None
