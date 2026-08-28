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

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC", DEFAULT_DB_URL_SYNC)

# If PostgreSQL requested but psycopg2 missing or offline, fall back to SQLite
if "postgresql" in DATABASE_URL_SYNC:
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
