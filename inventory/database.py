"""
Database configuration and session factories.

Supports two modes:
  1. Default DB  — single shared SQLite (backward-compatible, sequential runs)
  2. Session DB  — per-session isolated SQLite via SessionDatabaseManager

Routes use get_db() which checks for an X-Session-ID header:
  - If present → returns a session-scoped DB (isolated)
  - If absent  → returns the default shared DB
"""

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Header
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/app.db")

# ── Default engine (shared DB — backward compatible) ──
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_default_db():
    """Yield a session from the default (shared) database."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    """
    Dependency that returns the appropriate DB session.

    If X-Session-ID header is provided → returns session-scoped isolated DB.
    If no header → returns default shared DB (backward compatible).
    """
    if x_session_id:
        # Lazy import to avoid circular dependency
        from session_manager import session_manager

        async_session = await session_manager.get_session(x_session_id)
        async with async_session as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    else:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables in the default database."""
    # Import models so Base.metadata knows about all tables
    from models.product import Product  # noqa: F401
    from models.order import Order, OrderItem  # noqa: F401

    print(f"[init_db] Tables to create: {list(Base.metadata.tables.keys())}")
    print(f"[init_db] Engine URL: {engine.url}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[init_db] Tables created successfully.")