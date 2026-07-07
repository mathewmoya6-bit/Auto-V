# app/services/supabase_service.py
# =============================================================================
# AUTO-V API - Supabase Service
# =============================================================================

import logging
from typing import Optional, Dict, Any, List
from supabase import Client

from app.core.database import get_supabase, get_admin_client

logger = logging.getLogger(__name__)


class SupabaseService:
    """Base service for Supabase operations."""
    
    def __init__(self, use_admin: bool = False):
        self.client: Client = get_admin_client() if use_admin else get_supabase()
        self.use_admin = use_admin
    
    def _get_table(self, table_name: str):
        """Get a table reference."""
        return self.client.table(table_name)
    
    def select(self, table: str, columns: str = "*", filters: Optional[Dict] = None) -> List[Dict]:
        """Select records from a table."""
        try:
            query = self._get_table(table).select(columns)
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Select error on {table}: {e}")
            raise
    
    def select_one(self, table: str, filters: Dict, columns: str = "*") -> Optional[Dict]:
        """Select a single record from a table."""
        try:
            query = self._get_table(table).select(columns)
            for key, value in filters.items():
                query = query.eq(key, value)
            result = query.single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Select one error on {table}: {e}")
            return None
    
    def insert(self, table: str, data: Dict) -> Dict:
        """Insert a record into a table."""
        try:
            result = self._get_table(table).insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Insert error on {table}: {e}")
            raise
    
    def update(self, table: str, data: Dict, filters: Dict) -> Dict:
        """Update records in a table."""
        try:
            query = self._get_table(table).update(data)
            for key, value in filters.items():
                query = query.eq(key, value)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Update error on {table}: {e}")
            raise
    
    def delete(self, table: str, filters: Dict) -> bool:
        """Delete records from a table."""
        try:
            query = self._get_table(table).delete()
            for key, value in filters.items():
                query = query.eq(key, value)
            query.execute()
            return True
        except Exception as e:
            logger.error(f"Delete error on {table}: {e}")
            raise


__all__ = ["SupabaseService"]
