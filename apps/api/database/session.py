"""
Database Session Management for NETRA-X Backend
Supports PostgreSQL asyncpg / psycopg2 and SQLite fallback for local standalone testing.
"""

import os
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

# Default to SQLite fallback if Postgres is not configured locally
DEFAULT_DB_URL = "sqlite+aiosqlite:///./netrax.db"
DEFAULT_DB_URL_SYNC = "sqlite:///./netrax.db"

# Normalize environment DB URLs (Render provides postgres:// or postgresql://)
raw_db_url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

if raw_db_url.startswith("postgres://"):
    DATABASE_URL = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    raw_sync_default = raw_db_url.replace("postgres://", "postgresql://", 1)
elif raw_db_url.startswith("postgresql://") and not raw_db_url.startswith("postgresql+asyncpg://"):
    DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    raw_sync_default = raw_db_url
else:
    DATABASE_URL = raw_db_url
    raw_sync_default = DEFAULT_DB_URL_SYNC

DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC", raw_sync_default)

# If PostgreSQL requested but psycopg2 missing or offline, fall back to SQLite
if "postgresql" in DATABASE_URL_SYNC or "postgres" in DATABASE_URL_SYNC:
    try:
        import psycopg2
    except ImportError:
        DATABASE_URL = "sqlite+aiosqlite:///./netrax.db"
        DATABASE_URL_SYNC = "sqlite:///./netrax.db"

if "sqlite" in DATABASE_URL_SYNC:
    async_engine = create_async_engine(DATABASE_URL, echo=False)
    sync_engine = create_engine(DATABASE_URL_SYNC, echo=False, connect_args={"check_same_thread": False})
else:
    async_engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    sync_engine = create_engine(DATABASE_URL_SYNC, echo=False, pool_pre_ping=True)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def init_db_sync():
    """Synchronous DB table creation for seed/testing."""
    Base.metadata.create_all(bind=sync_engine)
