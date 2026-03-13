"""
Database engine and session factories for the Payment Gateway.

Two modes:
  1. Default DB — single shared SQLite for sequential runs
  2. Session DB — per-session isolated SQLite for concurrent evaluation

Routes use get_db() which checks for an X-Session-ID header:
  - Present → returns a session-scoped DB (isolated)
  - Absent  → returns the default shared DB
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

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all Payment Gateway SQLAlchemy models."""
    pass


async def get_session_id(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")) -> Optional[str]:
    """FastAPI dependency — extracts the X-Session-ID header value."""
    return x_session_id


async def get_db(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    """
    FastAPI dependency — returns the appropriate DB session.

    If X-Session-ID is present → session-scoped isolated DB.
    Otherwise → default shared DB.
    """
    if x_session_id:
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
    # Import models so Base.metadata picks up all tables
    import models  # noqa: F401

    print(f"[init_db] Tables to create: {list(Base.metadata.tables.keys())}")
    print(f"[init_db] Engine URL: {engine.url}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[init_db] Tables created successfully.")
