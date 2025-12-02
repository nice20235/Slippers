from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import QueuePool
from typing import AsyncGenerator
import os
import logging
import asyncio
from urllib.parse import quote_plus
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from sqlalchemy.engine import make_url

# Optional PostgreSQL bootstrap dependency
try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    psycopg2 = None  # fall back if not installed

logger = logging.getLogger(__name__)

# Database URL from settings - PostgreSQL only
DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)

# PostgreSQL optimized engine - high performance configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=QueuePool,
    pool_size=50,  # Increased from 20 for higher concurrency
    max_overflow=100,  # Increased from 30 for burst traffic
    pool_pre_ping=True,
    pool_recycle=1800,  # Recycle connections every 30min
    pool_timeout=10,  # Reduced timeout for faster failure detection
    connect_args={
        "command_timeout": 30,  # Reduced from 60s
        "server_settings": {
            "jit": "off",  # JIT disabled for predictable performance
            "statement_timeout": "30000",  # 30s query timeout
            "idle_in_transaction_session_timeout": "60000",  # Kill idle txns after 1min
        },
        "prepared_statement_cache_size": 500,  # Cache prepared statements
    },
    # Enable query result caching and execution options
    execution_options={
        "compiled_cache": {},  # Enable SQLAlchemy query compilation cache
    },
)

# Create async session factory with optimizations
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Better for async operations - prevents lazy loads after commit
    autocommit=False,
    autoflush=False,  # Manual control over when to flush - reduces round trips
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
        except Exception:
            await session.rollback()
            # Log full stack trace and exception details for unexpected errors
            logger.exception("Database session error")
            raise
        # Do not call session.close() here: context manager handles it


def _make_libpq_dsn(sa_url: str, override_db: str | None = None) -> str:
    """Convert SQLAlchemy URL (possibly with +asyncpg) to libpq DSN string for psycopg2."""
    url = make_url(sa_url)
    # Normalize driver
    if url.drivername.startswith("postgresql+"):
        _ = "postgresql"
    database = override_db or (url.database or "postgres")
    user = url.username or ""
    password = url.password or ""
    host = url.host or "localhost"
    port = url.port or 5432
    auth = f"user={quote_plus(user)} " if user else ""
    pwd = f"password={quote_plus(password)} " if password else ""
    return f"dbname={quote_plus(database)} {auth}{pwd}host={host} port={port}".strip()


def _ensure_database_exists_sync(sa_url: str) -> bool:
    """Ensure the target PostgreSQL database exists. Returns True if created or False otherwise."""
    if psycopg2 is None:
        return False
    url = make_url(sa_url)
    if not url.drivername.startswith("postgresql"):
        return False
    target_db = url.database
    if not target_db:
        return False
    # Connect to maintenance DB
    admin_dsn = _make_libpq_dsn(sa_url, override_db="postgres")
    created = False
    try:
        with psycopg2.connect(admin_dsn) as conn:  # type: ignore
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (target_db,))
                exists = cur.fetchone() is not None
                if not exists:
                    owner = url.username
                    if owner:
                        cur.execute(
                            f'CREATE DATABASE "{target_db}" OWNER "{owner}" ENCODING \'UTF8\''
                        )
                    else:
                        cur.execute(f"CREATE DATABASE \"{target_db}\" ENCODING 'UTF8'")
                    created = True
    except Exception as e:  # pragma: no cover
        logger.warning("Auto-create DB failed or not permitted: %s", e)
    return created


# Initialize database tables
async def init_db():
    """Initialize database tables - PostgreSQL only"""
    # Create database if missing (PostgreSQL)
    try:
        await asyncio.to_thread(_ensure_database_exists_sync, DATABASE_URL)
    except Exception as e:
        logger.warning("DB auto-create check skipped/failed: %s", e)

    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models.user import User  # noqa: F401
        from app.models.slipper import Slipper, Category, SlipperImage  # noqa: F401
        from app.models.order import Order, OrderItem  # noqa: F401
        from app.models.cart import Cart, CartItem  # noqa: F401
        from app.models.payment import Payment  # noqa: F401

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created successfully!")


# Close database connections
async def close_db():
    """Close database connections"""
    await engine.dispose()
