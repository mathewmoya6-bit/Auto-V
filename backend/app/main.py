# main.py
# =============================================================================
# AUTO-V API - Main Application Entry Point
# =============================================================================

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db, is_database_configured, engine
from app.api.v1.routes import auth, mileage

# ─── Import ALL models to register them with SQLAlchemy ────────────
# This is CRITICAL - all models must be imported so Base.metadata knows about them
from app.models import Base  # Base is imported first
from app.models.user import UserProfile
from app.models.vehicle import Vehicle, VehicleImage, VINScan
from app.models.mileage import VehicleCategory, VehicleVariant, Route, MileageClaim

# ─── Setup Logging ──────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Lifespan Manager ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📌 Environment: {settings.ENV}")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info(f"🗄️  Database configured: {is_database_configured()}")
    logger.info(f"🌐 CORS_ORIGINS: {settings.CORS_ORIGINS}")
    logger.info("=" * 60)
    
    if is_database_configured():
        try:
            # Initialize database connection
            await init_db()
            logger.info("✅ Database initialized successfully")
            
            # ─── CREATE TABLES IF THEY DON'T EXIST ────────────────────
            # CRITICAL: This creates ALL tables defined in your models
            # Only use in development or if you're sure about the schema
            if settings.ENV in ["development", "test"]:
                logger.info("📋 Creating database tables if they don't exist...")
                async with engine.begin() as conn:
                    # This creates all tables defined in your models
                    await conn.run_sync(Base.metadata.create_all)
                logger.info("✅ Database tables verified/created successfully")
            else:
                logger.info("ℹ️  Skipping table creation in production mode")
                logger.info("   Tables should be managed via migrations or SQL scripts")
            
            # Verify tables exist
            async with engine.connect() as conn:
                result = await conn.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'users'"
                )
                user_table_count = result.scalar()
                if user_table_count > 0:
                    logger.info("✅ Verified: 'users' table exists")
                else:
                    logger.warning("⚠️  'users' table not found - some features may not work")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {str(e)}")
            # In production, we might want to continue but log the error
            if settings.ENV in ["development", "test"]:
                raise
    
    yield
    
    # Shutdown
    await close_db()
    logger.info("👋 Application shutdown complete")


# ─── Create FastAPI App ────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Professional Vehicle Valuation Engine API",
    docs_url="/docs" if settings.ENABLE_SWAGGER else None,
    redoc_url="/redoc" if settings.ENABLE_SWAGGER else None,
    openapi_url="/openapi.json" if settings.ENABLE_SWAGGER else None,
    lifespan=lifespan,
)


# ─── CORS Middleware ───────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Response-Time"],
)


# ─── Register Routes ──────────────────────────────────────────────

# Make sure the auth router exists before including it
try:
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Authentication"])
    logger.info("✅ Auth routes registered")
except AttributeError:
    logger.warning("⚠️  Auth router not available - skipping")

app.include_router(mileage.router, prefix=settings.API_V1_PREFIX, tags=["Mileage"])
logger.info("✅ Mileage routes registered")

logger.info("✅ All routes registered successfully")


# ─── Health & Root Endpoints ──────────────────────────────────────

@app.get("/health")
async def health_check():
    db_status = "unknown"
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "debug": settings.DEBUG,
        "database": db_status,
        "database_configured": is_database_configured(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "docs": "/docs" if settings.ENABLE_SWAGGER else "disabled",
        "health": "/health",
        "api_prefix": settings.API_V1_PREFIX,
    }


# ─── Debug Endpoint ──────────────────────────────────────────────

@app.get("/debug/db")
async def test_db():
    """Test database connection and list tables."""
    try:
        async with engine.connect() as conn:
            # Test connection
            result = await conn.execute("SELECT 1")
            db_connected = result.scalar() == 1
            
            # Get list of tables
            tables = await conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
            table_list = [row[0] for row in tables.fetchall()]
            
            # Check for required tables
            required_tables = ['users', 'vehicles', 'vehicle_categories', 'vehicle_variants', 'mileage_claims', 'routes']
            table_status = {table: table in table_list for table in required_tables}
            
            # Get count of records in key tables
            counts = {}
            for table in required_tables:
                if table in table_list:
                    try:
                        count_result = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                        counts[table] = count_result.scalar()
                    except:
                        counts[table] = "error"
            
            return {
                "status": "✅ Connected!" if db_connected else "❌ Failed",
                "database_url": settings.DATABASE_URL[:50] + "..." if settings.DATABASE_URL else None,
                "tables": table_list,
                "table_count": len(table_list),
                "required_tables_present": all(table_status.values()),
                "table_status": table_status,
                "record_counts": counts,
            }
    except Exception as e:
        return {
            "status": "❌ Failed",
            "error": str(e),
            "database_configured": is_database_configured(),
        }


# ─── Model Registration Debug Endpoint ────────────────────────────

@app.get("/debug/models")
async def debug_models():
    """Check which models are registered with SQLAlchemy."""
    try:
        # Get all mapped classes
        mapper_registry = Base.metadata
        tables = mapper_registry.tables.keys()
        classes = {}
        
        # Get class names from tables
        for table_name in tables:
            # Find the class associated with this table
            for cls in Base.__subclasses__():
                if hasattr(cls, '__tablename__') and cls.__tablename__ == table_name:
                    classes[table_name] = cls.__name__
                    break
            else:
                classes[table_name] = "No class found"
        
        return {
            "registered_tables": list(tables),
            "table_count": len(tables),
            "class_mapping": classes,
            "all_subclasses": [cls.__name__ for cls in Base.__subclasses__()],
        }
    except Exception as e:
        return {"status": "❌ Failed", "error": str(e)}


# ─── Main Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", settings.PORT))
    host = os.getenv("HOST", settings.HOST)
    debug = settings.DEBUG
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1,
    )
