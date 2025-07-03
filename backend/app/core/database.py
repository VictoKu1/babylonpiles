"""
Database configuration and initialization
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Convert SQLite URL to async
if settings.database_url.startswith("sqlite"):
    database_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    database_url = settings.database_url

# Create async engine
engine = create_async_engine(
    database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Metadata for migrations (renamed to avoid conflict)
db_metadata = MetaData()

async def init_db():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            # Import models to register them
            from app.models import pile, user, update_log, system_status
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed") 