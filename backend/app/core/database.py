# app/core/database.py
# =============================================================================
# AUTO-V API - Database Core (Supabase Native)
# =============================================================================

import logging
from typing import Optional, Dict, Any, Generator
from contextlib import contextmanager
from functools import lru_cache

from supabase import create_client, Client
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Client Container ─────────────────────────────────────────────────

class SupabaseClients:
    """Container for Supabase clients."""
    
    def __init__(self):
        self._public: Optional[Client] = None
        self._admin: Optional[Client] = None
        self._initialized: bool = False
    
    @property
    def public(self) -> Client:
        """Get the public Supabase client."""
        if not self._public:
            raise RuntimeError("Supabase public client not initialized")
        return self._public
    
    @property
    def admin(self) -> Client:
        """Get the admin Supabase client."""
        if not self._admin:
            raise RuntimeError("Supabase admin client not initialized")
        return self._admin
    
    @property
    def initialized(self) -> bool:
        """Check if clients are initialized."""
        return self._initialized
    
    def init(self) -> bool:
        """
        Initialize Supabase clients.
        
        Returns:
            True if initialized successfully, False otherwise
        """
        try:
            if not settings.supabase_configured:
                logger.warning("⚠️  Supabase credentials not configured")
                return False
            
            # Public client
            self._public = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_ANON_KEY
            )
            logger.info("✅ Supabase public client initialized")
            
            # Admin client (if service role key is available)
            if settings.SUPABASE_SERVICE_ROLE_KEY:
                self._admin = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_ROLE_KEY
                )
                logger.info("✅ Supabase admin client initialized")
            else:
                logger.info("ℹ️  Supabase admin client not configured")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase: {e}")
            self._initialized = False
            return False
    
    def reset(self) -> None:
        """Reset clients (useful for testing)."""
        self._public = None
        self._admin = None
        self._initialized = False


# ─── Singleton Instance ─────────────────────────────────────────────

_clients = SupabaseClients()


# ─── Initialization Function ────────────────────────────────────────

def init_supabase() -> bool:
    """
    Initialize Supabase clients.
    
    Call this during FastAPI startup.
    
    Returns:
        True if initialized successfully, False otherwise
    """
    return _clients.init()


def reset_supabase() -> None:
    """Reset Supabase clients (for testing)."""
    _clients.reset()


# ─── Client Getter Functions ─────────────────────────────────────────

@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """
    Get the public Supabase client.
    
    Use this for regular authenticated requests.
    
    Returns:
        Supabase client instance
        
    Raises:
        RuntimeError: If client is not initialized
    """
    return _clients.public


@lru_cache(maxsize=1)
def get_admin_client() -> Client:
    """
    Get the admin Supabase client (with service role key).
    
    Use this for admin operations that bypass RLS.
    
    Returns:
        Supabase admin client instance
        
    Raises:
        RuntimeError: If client is not initialized
    """
    return _clients.admin


def is_configured() -> bool:
    """
    Check if Supabase is configured and initialized.
    
    Returns:
        True if Supabase is configured, False otherwise
    """
    return _clients.initialized


# ─── Dependency Injection ────────────────────────────────────────────

def get_db() -> Generator[Client, None, None]:
    """
    Dependency injection for Supabase client.
    
    Use this with FastAPI Depends:
    
        @router.get("/vehicles")
        async def get_vehicles(db: Client = Depends(get_db)):
            result = db.table("vehicles").select("*").execute()
            return result.data
    
    Yields:
        Supabase client instance
    """
    if not _clients.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured"
        )
    
    yield _clients.public


def get_db_admin() -> Generator[Client, None, None]:
    """
    Dependency injection for admin Supabase client.
    
    Use this for admin-only operations.
    
    Yields:
        Supabase admin client instance
    """
    if not _clients.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured"
        )
    
    if not _clients.admin:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin database client not configured"
        )
    
    yield _clients.admin


# ─── Query Helpers ────────────────────────────────────────────────────

class SupabaseQuery:
    """Fluent query builder for Supabase."""
    
    def __init__(self, table: str, client: Optional[Client] = None):
        self.table_name = table
        self.client = client or get_supabase()
        self._query = self.client.table(table)
        self._filters = []
    
    def select(self, columns: str = "*") -> "SupabaseQuery":
        """Select columns."""
        self._query = self._query.select(columns)
        return self
    
    def eq(self, column: str, value: Any) -> "SupabaseQuery":
        """Equal filter."""
        self._query = self._query.eq(column, value)
        return self
    
    def neq(self, column: str, value: Any) -> "SupabaseQuery":
        """Not equal filter."""
        self._query = self._query.neq(column, value)
        return self
    
    def gt(self, column: str, value: Any) -> "SupabaseQuery":
        """Greater than filter."""
        self._query = self._query.gt(column, value)
        return self
    
    def gte(self, column: str, value: Any) -> "SupabaseQuery":
        """Greater than or equal filter."""
        self._query = self._query.gte(column, value)
        return self
    
    def lt(self, column: str, value: Any) -> "SupabaseQuery":
        """Less than filter."""
        self._query = self._query.lt(column, value)
        return self
    
    def lte(self, column: str, value: Any) -> "SupabaseQuery":
        """Less than or equal filter."""
        self._query = self._query.lte(column, value)
        return self
    
    def like(self, column: str, pattern: str) -> "SupabaseQuery":
        """Like filter."""
        self._query = self._query.like(column, pattern)
        return self
    
    def ilike(self, column: str, pattern: str) -> "SupabaseQuery":
        """Case-insensitive like filter."""
        self._query = self._query.ilike(column, pattern)
        return self
    
    def is_(self, column: str, value: Any) -> "SupabaseQuery":
        """Is filter (for NULL checks)."""
        self._query = self._query.is_(column, value)
        return self
    
    def in_(self, column: str, values: list) -> "SupabaseQuery":
        """In filter."""
        self._query = self._query.in_(column, values)
        return self
    
    def order(self, column: str, desc: bool = False) -> "SupabaseQuery":
        """Order by."""
        self._query = self._query.order(column, desc=desc)
        return self
    
    def limit(self, count: int) -> "SupabaseQuery":
        """Limit results."""
        self._query = self._query.limit(count)
        return self
    
    def range(self, start: int, end: int) -> "SupabaseQuery":
        """Range filter."""
        self._query = self._query.range(start, end)
        return self
    
    def single(self) -> "SupabaseQuery":
        """Get single result."""
        self._query = self._query.single()
        return self
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute the query.
        
        Returns:
            Query result with 'data' and 'count' fields
            
        Raises:
            HTTPException: On query error
        """
        try:
            result = self._query.execute()
            return {
                "data": result.data,
                "count": len(result.data) if result.data else 0,
                "error": None
            }
        except Exception as e:
            logger.error(f"❌ Query error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database query failed: {str(e)}"
            )
    
    def execute_or_404(self) -> Dict[str, Any]:
        """
        Execute query and raise 404 if no results.
        
        Returns:
            Query result with 'data' field
            
        Raises:
            HTTPException: 404 if no results
        """
        result = self.execute()
        if not result["data"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource not found in {self.table_name}"
            )
        return result


# ─── Table Helpers ───────────────────────────────────────────────────

def table(table_name: str, client: Optional[Client] = None) -> SupabaseQuery:
    """
    Start a query on a table.
    
    Args:
        table_name: Name of the table
        client: Optional client override
        
    Returns:
        SupabaseQuery instance
        
    Example:
        result = table("vehicles").select("*").eq("make", "Toyota").execute()
        return result["data"]
    """
    return SupabaseQuery(table_name, client)


def insert(table_name: str, data: Dict[str, Any], client: Optional[Client] = None) -> Dict[str, Any]:
    """
    Insert data into a table.
    
    Args:
        table_name: Name of the table
        data: Data to insert
        client: Optional client override
        
    Returns:
        Inserted data
        
    Raises:
        HTTPException: On insert error
    """
    try:
        db = client or get_supabase()
        result = db.table(table_name).insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"❌ Insert error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert into {table_name}: {str(e)}"
        )


def update(table_name: str, data: Dict[str, Any], filters: Dict[str, Any], client: Optional[Client] = None) -> Dict[str, Any]:
    """
    Update data in a table.
    
    Args:
        table_name: Name of the table
        data: Data to update
        filters: Filters for the update
        client: Optional client override
        
    Returns:
        Updated data
        
    Raises:
        HTTPException: On update error
    """
    try:
        db = client or get_supabase()
        query = db.table(table_name).update(data)
        for key, value in filters.items():
            query = query.eq(key, value)
        result = query.execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"❌ Update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update {table_name}: {str(e)}"
        )


def delete(table_name: str, filters: Dict[str, Any], client: Optional[Client] = None) -> bool:
    """
    Delete data from a table.
    
    Args:
        table_name: Name of the table
        filters: Filters for the delete
        client: Optional client override
        
    Returns:
        True if deleted successfully
        
    Raises:
        HTTPException: On delete error
    """
    try:
        db = client or get_supabase()
        query = db.table(table_name).delete()
        for key, value in filters.items():
            query = query.eq(key, value)
        query.execute()
        return True
    except Exception as e:
        logger.error(f"❌ Delete error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete from {table_name}: {str(e)}"
        )


# ─── Export Public API ─────────────────────────────────────────────

__all__ = [
    # Initialization
    "init_supabase",
    "reset_supabase",
    "is_configured",
    
    # Clients
    "get_supabase",
    "get_admin_client",
    "get_db",
    "get_db_admin",
    
    # Query Helpers
    "SupabaseQuery",
    "table",
    "insert",
    "update",
    "delete",
]


# ─── Module Logger ──────────────────────────────────────────────────

logger.info("📦 Database module loaded")
