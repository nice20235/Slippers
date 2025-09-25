from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy import event
from typing import AsyncGenerator
import os
import logging
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)

# Database URL - use SQLite for development, can be changed to PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./slippers.db")

# Create async engine with optimized settings
if "sqlite" in DATABASE_URL:
    # SQLite-specific optimizations
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        poolclass=StaticPool,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,  # Increased timeout
            "isolation_level": None,
        }
    )
else:
    # PostgreSQL/MySQL optimizations
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_timeout=30,
        connect_args={
            "command_timeout": 60,
            "server_settings": {
                "jit": "off",
            }
        }
    )

# Create async session factory with optimizations
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Better for async operations
    autocommit=False,
    autoflush=False,  # Manual control over when to flush
)

# Base class for all models
class Base(DeclarativeBase):
    pass

# Dependency to get database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Optimized dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except HTTPException:
            # Expected API error paths: rollback without noisy error logs
            await session.rollback()
            raise
        except RequestValidationError:
            # Validation errors occur before hitting business logic; treat quietly
            await session.rollback()
            raise
        except Exception as e:
            await session.rollback()
            # Log full stack trace and exception details for unexpected errors
            logger.exception("Database session error")
            raise
        # Do not call session.close() here: context manager handles it

# Initialize database tables
async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models.user import User  # noqa: F401
        from app.models.slipper import Slipper, Category, SlipperImage  # noqa: F401
        from app.models.order import Order, OrderItem  # noqa: F401
        from app.models.payment import Payment  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")

# Close database connections
async def close_db():
    """Close database connections"""
    await engine.dispose()