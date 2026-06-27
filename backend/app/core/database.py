# app/core/database.py
from supabase import create_client, Client
from typing import Optional, Dict, Any
import logging
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    """Supabase database client wrapper"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the database connection"""
        try:
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            self._initialized = True
            logger.info("Database connection established successfully")
            
            # Test connection
            await self.test_connection()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def test_connection(self):
        """Test database connection"""
        try:
            # Simple query to test connection
            response = self.client.table('users').select('count').limit(1).execute()
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            raise
    
    async def close(self):
        """Close database connection"""
        if self.client:
            # Supabase client doesn't have explicit close method
            self.client = None
            self._initialized = False
            logger.info("Database connection closed")
    
    def get_client(self) -> Client:
        """Get the Supabase client instance"""
        if not self._initialized or not self.client:
            raise RuntimeError("Database not initialized")
        return self.client
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions"""
        client = self.get_client()
        try:
            yield client
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            raise

# Global database instance
db = Database()

async def init_db():
    """Initialize database on application startup"""
    await db.initialize()

async def close_db():
    """Close database on application shutdown"""
    await db.close()

def get_db() -> Client:
    """Dependency for getting database client"""
    return db.get_client()
