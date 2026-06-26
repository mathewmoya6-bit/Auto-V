"""
Database Module - Supabase Client Wrapper
"""

from app.core.supabase_client import (
    get_supabase,
    async_get_supabase,
    get_supabase_status,
    force_supabase_connection,
    check_supabase_health,
    async_check_supabase_health,
    reset_supabase_client
)

# ─── Convenience Exports ──────────────────────────────────────

__all__ = [
    'get_supabase',
    'async_get_supabase',
    'get_supabase_status',
    'force_supabase_connection',
    'check_supabase_health',
    'async_check_supabase_health',
    'reset_supabase_client'
]

# ─── Singleton Instance ──────────────────────────────────────

# Initialize the client once on module load
try:
    supabase = get_supabase()
    logger = logging.getLogger(__name__)
    logger.info("✅ Supabase client ready")
except Exception as e:
    supabase = None
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Supabase client initialization failed: {e}")

# ─── Async Version for FastAPI ──────────────────────────────

async def get_supabase_async() -> Client:
    """
    Get Supabase client asynchronously.
    """
    return await async_get_supabase()
