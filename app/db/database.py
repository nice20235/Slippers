from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy import event
from typing import AsyncGenerator
import os
import logging
import asyncio
from urllib.parse import quote_plus
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from sqlalchemy.engine import make_url

# Optional deps used during bootstrap (PostgreSQL creation / migration)
try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    psycopg2 = None  # fall back if not installed
try:
    import sqlite3  # type: ignore
except Exception:  # pragma: no cover
    sqlite3 = None

logger = logging.getLogger(__name__)

# Database URL comes from pydantic settings (.env) with sane default to PostgreSQL
# Fallback to env var for backward compatibility
DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)

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
    # Ensure important PRAGMAs are set for every connection
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):  # noqa: D401
        """Set SQLite PRAGMAs for FK enforcement and better journaling."""
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.close()
        except Exception:
            # Best-effort; continue even if PRAGMAs can't be set
            pass
else:
    # PostgreSQL/MySQL optimizations - tuned for high performance
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=QueuePool,
        pool_size=50,           # Increased from 20 for higher concurrency
        max_overflow=100,       # Increased from 30 for burst traffic
        pool_pre_ping=True,
        pool_recycle=1800,      # Recycle connections every 30min (was 1hr)
        pool_timeout=10,        # Reduced timeout for faster failure detection
        connect_args={
            "command_timeout": 30,  # Reduced from 60s
            "server_settings": {
                "jit": "off",                    # JIT disabled for predictable performance
                "statement_timeout": "30000",    # 30s query timeout
                "idle_in_transaction_session_timeout": "60000",  # Kill idle txns after 1min
            },
            "prepared_statement_cache_size": 500,  # Cache prepared statements
        },
        # Enable query result caching and execution options
        execution_options={
            "compiled_cache": {},  # Enable SQLAlchemy query compilation cache
        }
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
        except Exception as e:
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
                        cur.execute(f"CREATE DATABASE \"{target_db}\" OWNER \"{owner}\" ENCODING 'UTF8'")
                    else:
                        cur.execute(f"CREATE DATABASE \"{target_db}\" ENCODING 'UTF8'")
                    created = True
    except Exception as e:  # pragma: no cover
        logger.warning("Auto-create DB failed or not permitted: %s", e)
    return created


def _is_postgres_db_empty_sync(sa_url: str) -> bool:
    """Return True if the application tables in the PostgreSQL DB contain no rows.

    Strategy: after SQLAlchemy create_all, core tables will exist. We check a set of key tables.
    Consider DB 'empty' if none of the tables contain any rows.
    """
    if psycopg2 is None:
        # If psycopg2 missing, we conservatively assume not empty to avoid unintended migration
        return False
    url = make_url(sa_url)
    if not url.drivername.startswith("postgresql"):
        return False
    dsn = _make_libpq_dsn(sa_url)
    tables_to_check = [
        "users",
        "categories",
        "slippers",
        "slipper_images",
        "carts",
        "cart_items",
        "orders",
        "order_items",
        "payments",
    ]
    try:
        with psycopg2.connect(dsn) as conn:  # type: ignore
            with conn.cursor() as cur:
                any_rows = False
                for t in tables_to_check:
                    cur.execute(
                        """
                        SELECT EXISTS (
                          SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s
                        )
                        """,
                        (t,)
                    )
                    exists = cur.fetchone()[0]
                    if not exists:
                        continue
                    cur.execute(f"SELECT EXISTS (SELECT 1 FROM \"{t}\" LIMIT 1);")
                    has = cur.fetchone()[0]
                    if has:
                        any_rows = True
                        break
                return not any_rows
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to assess DB emptiness: %s", e)
        return False


def _migrate_sqlite_to_postgres_sync(sqlite_path: str, sa_url: str) -> None:
    """Migrate all user tables from a local SQLite file into the current PostgreSQL database.

    Uses the generic per-table copy from scripts.migrate_data.migrate_table and logs progress.
    Assumes SQLAlchemy has already created the target schema.
    """
    if psycopg2 is None or sqlite3 is None:
        logger.warning("Migration skipped: drivers not available (psycopg2 or sqlite3 missing)")
        return
    if not os.path.exists(sqlite_path):
        logger.warning("Migration skipped: SQLite file not found at %s", sqlite_path)
        return
    dsn = _make_libpq_dsn(sa_url)
    try:
        import scripts.migrate_data as md  # type: ignore
    except Exception as e:  # pragma: no cover
        logger.warning("Migration module not found/failed to import: %s", e)
        return

    # Determine table list and apply priority order to satisfy FKs
    priority = [
        "categories",
        "users",
        "slippers",
        "slipper_images",
        "carts",
        "orders",
        "payments",
        "cart_items",
        "order_items",
    ]
    try:
        with sqlite3.connect(sqlite_path) as sconn:  # type: ignore
            sconn.row_factory = sqlite3.Row  # type: ignore
            scur = sconn.cursor()
            scur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
            all_tables = [r[0] for r in scur.fetchall()]
            ordered = [t for t in priority if t in all_tables]
            rest = [t for t in all_tables if t not in ordered]
            tables = ordered + sorted(rest)
            logger.info("Starting SQLite -> PostgreSQL migration: %d tables", len(tables))
            with psycopg2.connect(dsn) as pg:  # type: ignore
                for t in tables:
                    try:
                        logger.info("Migrating table %s ...", t)
                        md.migrate_table(sconn, pg, t, batch_size=1000)
                        logger.info("Table %s migrated", t)
                    except Exception as e:
                        logger.exception("Failed migrating table %s: %s", t, e)
                        raise
                # After all data migrated, reset sequences to prevent duplicate key errors
                logger.info("Resetting PostgreSQL sequences...")
                _reset_postgres_sequences_sync(pg)
            logger.info("SQLite -> PostgreSQL migration completed successfully")
    except Exception as e:  # pragma: no cover
        logger.warning("Migration aborted due to error: %s", e)


def _reset_postgres_sequences_sync(pg_conn) -> None:
    """Reset all PostgreSQL sequences to match the max ID in their tables.
    
    This prevents 'duplicate key' errors after migrating data from SQLite.
    """
    try:
        with pg_conn.cursor() as cur:
            # Find all sequences and their associated tables
            cur.execute("""
                SELECT 
                    t.table_name,
                    c.column_name,
                    pg_get_serial_sequence(quote_ident(t.table_name), quote_ident(c.column_name)) as sequence_name
                FROM information_schema.tables t
                JOIN information_schema.columns c 
                    ON t.table_name = c.table_name
                WHERE t.table_schema = 'public'
                    AND c.column_default LIKE 'nextval%'
                    AND t.table_type = 'BASE TABLE'
            """)
            
            sequences = cur.fetchall()
            for table_name, column_name, sequence_name in sequences:
                if sequence_name:
                    try:
                        # Get max ID from table
                        cur.execute(f'SELECT MAX("{column_name}") FROM "{table_name}"')
                        max_id = cur.fetchone()[0]
                        
                        if max_id is not None:
                            # Set sequence to max_id + 1
                            cur.execute(f"SELECT setval('{sequence_name}', %s, true)", (max_id,))
                            logger.info(f"Reset sequence {sequence_name} to {max_id}")
                    except Exception as e:
                        logger.warning(f"Failed to reset sequence {sequence_name}: {e}")
            
            pg_conn.commit()
            logger.info("All sequences reset successfully")
    except Exception as e:
        logger.warning(f"Sequence reset failed: {e}")

# Initialize database tables
async def init_db():
    """Initialize database tables"""
    # If target is PostgreSQL, attempt to create the database if missing (non-fatal on failure)
    if engine.sync_engine.dialect.name == "postgresql":
        try:
            await asyncio.to_thread(_ensure_database_exists_sync, DATABASE_URL)
        except Exception as e:  # pragma: no cover
            logger.warning("DB auto-create check skipped/failed: %s", e)

    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models.user import User  # noqa: F401
        from app.models.slipper import Slipper, Category, SlipperImage  # noqa: F401
        from app.models.order import Order, OrderItem  # noqa: F401
        from app.models.cart import Cart, CartItem  # noqa: F401
        from app.models.payment import Payment  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")

        # After tables exist, if PostgreSQL DB is empty, run one-time migration from SQLite
        if engine.sync_engine.dialect.name == "postgresql":
            try:
                is_empty = await asyncio.to_thread(_is_postgres_db_empty_sync, DATABASE_URL)
                if is_empty:
                    logger.info("PostgreSQL DB is empty: starting one-time migration from SQLite")
                    sqlite_path = os.path.abspath(os.getenv("SQLITE_PATH", "./slippers.db"))
                    await asyncio.to_thread(_migrate_sqlite_to_postgres_sync, sqlite_path, DATABASE_URL)
                else:
                    logger.info("PostgreSQL DB has data: skipping auto-migration")
            except Exception as e:  # pragma: no cover
                logger.warning("Auto-migration step failed/skipped: %s", e)

        # Skip legacy SQLite-specific auto-migrations when not using SQLite
        if engine.sync_engine.dialect.name != "sqlite":
            logger.info("Non-SQLite dialect detected (%s): skipping SQLite-specific PRAGMA migrations", engine.sync_engine.dialect.name)
            return

        # --- Legacy status normalization (idempotent, SQLite) ---
        try:
            # Normalize to uppercase first (defensive) then map.
            await conn.exec_driver_sql(
                "UPDATE orders SET status=UPPER(status);"
            )
            await conn.exec_driver_sql(
                "UPDATE orders SET status='PAID' WHERE status IN ('confirmed','preparing','ready','delivered','paid');"
            )
            await conn.exec_driver_sql(
                "UPDATE orders SET status='PENDING' WHERE status IN ('cancelled','pending');"
            )
            await conn.exec_driver_sql(
                "UPDATE orders SET status='PENDING' WHERE status NOT IN ('PENDING','PAID','REFUNDED');"
            )
            logger.info("✅ Order status normalization completed (SQLite)")
        except Exception as e:
            logger.warning("Order status normalization skipped/failed: %s", e)

        # --- SQLite-only: add columns if missing via PRAGMA table_info ---
        try:
            res = await conn.exec_driver_sql("PRAGMA table_info(orders);")
            cols = [r[1] for r in res.fetchall()]  # r[1] is column name
            if 'payment_uuid' not in cols:
                logger.info("Adding missing payment_uuid column to orders table (auto-migration, SQLite)...")
                await conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN payment_uuid VARCHAR(64);")
                try:
                    await conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_orders_payment_uuid ON orders(payment_uuid);")
                except Exception:
                    pass
                try:
                    await conn.exec_driver_sql(
                        """
                        UPDATE orders
                        SET payment_uuid = (
                            SELECT p.octo_payment_uuid
                            FROM payments p
                            WHERE p.order_id = orders.id AND p.octo_payment_uuid IS NOT NULL
                            ORDER BY p.created_at DESC
                            LIMIT 1
                        )
                        WHERE payment_uuid IS NULL;
                        """
                    )
                except Exception as e:
                    logger.warning("Backfill payment_uuid skipped: %s", e)
                logger.info("payment_uuid column added & backfill attempted (SQLite)")
            else:
                try:
                    await conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_orders_payment_uuid ON orders(payment_uuid);")
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Auto-migration for payment_uuid failed/skipped: %s", e)

        try:
            res = await conn.exec_driver_sql("PRAGMA table_info(orders);")
            cols = [r[1] for r in res.fetchall()]
            if 'idempotency_key' not in cols:
                logger.info("Adding missing idempotency_key column to orders table (auto-migration, SQLite)...")
                await conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN idempotency_key VARCHAR(64);")
                try:
                    await conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_idempotency_key ON orders(idempotency_key);")
                except Exception:
                    pass
            else:
                try:
                    await conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_idempotency_key ON orders(idempotency_key);")
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Auto-migration for idempotency_key failed/skipped: %s", e)

        # --- Enforce unique constraints and cleanup (SQLite) ---
        try:
            await conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_order_items_order_slipper ON order_items(order_id, slipper_id);"
            )
        except Exception as e:
            logger.warning("Creating unique index for order_items failed/skipped: %s", e)

        try:
            await conn.exec_driver_sql(
                """
                UPDATE orders
                SET order_id = CAST(id AS TEXT)
                WHERE order_id IS NULL OR order_id = '' OR order_id = '0';
                """
            )
        except Exception as e:
            logger.warning("Order order_id cleanup skipped/failed: %s", e)

        try:
            await conn.exec_driver_sql("DROP TABLE IF EXISTS oi_sums;")
            await conn.exec_driver_sql("DROP TABLE IF EXISTS oi_keepers;")
            await conn.exec_driver_sql(
                """
                CREATE TEMP TABLE oi_sums AS
                SELECT order_id, slipper_id, SUM(quantity) AS sum_qty, MAX(unit_price) AS max_unit_price
                FROM order_items
                GROUP BY order_id, slipper_id;
                """
            )
            await conn.exec_driver_sql(
                """
                CREATE TEMP TABLE oi_keepers AS
                SELECT MIN(id) AS keep_id, order_id, slipper_id
                FROM order_items
                GROUP BY order_id, slipper_id;
                """
            )
            await conn.exec_driver_sql(
                """
                UPDATE order_items
                SET
                  quantity = (
                    SELECT s.sum_qty FROM oi_sums s
                    WHERE s.order_id = order_items.order_id AND s.slipper_id = order_items.slipper_id
                  ),
                  unit_price = (
                    SELECT s.max_unit_price FROM oi_sums s
                    WHERE s.order_id = order_items.order_id AND s.slipper_id = order_items.slipper_id
                  ),
                  total_price = (
                    (SELECT s.sum_qty FROM oi_sums s
                     WHERE s.order_id = order_items.order_id AND s.slipper_id = order_items.slipper_id)
                    *
                    (SELECT s.max_unit_price FROM oi_sums s
                     WHERE s.order_id = order_items.order_id AND s.slipper_id = order_items.slipper_id)
                  )
                WHERE id IN (SELECT keep_id FROM oi_keepers);
                """
            )
            await conn.exec_driver_sql(
                """
                DELETE FROM order_items
                WHERE id NOT IN (SELECT keep_id FROM oi_keepers);
                """
            )
            await conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_order_items_order_slipper ON order_items(order_id, slipper_id);"
            )
            logger.info("✅ Consolidated duplicate order_items and recomputed order totals (SQLite)")
        except Exception as e:
            logger.warning("Duplicate order_items consolidation skipped/failed: %s", e)

        try:
            try:
                await conn.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_carts_user ON carts(user_id);"
                )
            except Exception:
                pass
            await conn.exec_driver_sql("DROP TABLE IF EXISTS ci_sums;")
            await conn.exec_driver_sql("DROP TABLE IF EXISTS ci_keepers;")
            await conn.exec_driver_sql(
                """
                CREATE TEMP TABLE ci_sums AS
                SELECT cart_id, slipper_id, SUM(quantity) AS sum_qty
                FROM cart_items
                GROUP BY cart_id, slipper_id;
                """
            )
            await conn.exec_driver_sql(
                """
                CREATE TEMP TABLE ci_keepers AS
                SELECT MIN(id) AS keep_id, cart_id, slipper_id
                FROM cart_items
                GROUP BY cart_id, slipper_id;
                """
            )
            await conn.exec_driver_sql(
                """
                UPDATE cart_items
                SET quantity = (
                    SELECT s.sum_qty FROM ci_sums s
                    WHERE s.cart_id = cart_items.cart_id AND s.slipper_id = cart_items.slipper_id
                )
                WHERE id IN (SELECT keep_id FROM ci_keepers);
                """
            )
            await conn.exec_driver_sql(
                """
                DELETE FROM cart_items
                WHERE id NOT IN (SELECT keep_id FROM ci_keepers);
                """
            )
            try:
                await conn.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_cart_items_cart_slipper ON cart_items(cart_id, slipper_id);"
                )
            except Exception:
                pass
            logger.info("✅ Consolidated duplicate cart_items and enforced unique constraints (SQLite)")
        except Exception as e:
            logger.warning("Cart integrity safeguards skipped/failed: %s", e)

# Close database connections
async def close_db():
    """Close database connections"""
    await engine.dispose()