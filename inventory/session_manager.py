"""
Session Database Manager — per-session SQLite DB isolation.

Creates and manages isolated databases for concurrent evaluation sessions.
Each session gets its own SQLite file in data/sessions/, ensuring that
multiple agents evaluating simultaneously never interfere with each other.

This pattern is ONLY needed for gyms that have shared persistent state
(e.g., SQLite database). In-memory gyms don't need this because each
MCPEnvironment instance already has its own state.

Usage:
    manager = SessionDatabaseManager()
    session_id = await manager.create_session("my_session_123")
    async_session = await manager.get_session(session_id)
    # ... use the session ...
    await manager.delete_session(session_id)
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database import Base

# Base directory of the inventory gym (this file lives at inventory/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Import all models so Base.metadata knows about them
from models.product import Product  # noqa: F401
from models.order import Order, OrderItem  # noqa: F401

logger = logging.getLogger(__name__)

SESSIONS_DIR = os.path.join(BASE_DIR, "data", "sessions")


class SessionDatabaseManager:
    """
    Manages isolated SQLite databases per evaluation session.

    Each session creates a fresh, empty SQLite DB file with the full schema
    (products, orders, order_items). When the session is deleted, the file
    is removed.

    Thread-safe via asyncio.Lock for session creation/deletion.
    """

    def __init__(self, sessions_dir: str = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        self._engines: Dict[str, any] = {}
        self._session_makers: Dict[str, async_sessionmaker] = {}
        self._session_info: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

        os.makedirs(self.sessions_dir, exist_ok=True)

    def _get_db_path(self, session_id: str) -> str:
        """Get the SQLite file path for a session."""
        return os.path.join(self.sessions_dir, f"{session_id}.db")

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists (either in memory or on disk)."""
        return (
            session_id in self._engines
            or os.path.exists(self._get_db_path(session_id))
        )

    async def create_session(self, session_id: str) -> str:
        """
        Create a new session with an isolated SQLite database.

        Creates all tables (products, orders, order_items) in the new DB.
        If the session already exists, returns the existing session_id.

        Args:
            session_id: Unique identifier for this session.

        Returns:
            The session_id.
        """
        async with self._lock:
            if self.session_exists(session_id):
                # Ensure in-memory references exist
                if session_id not in self._engines:
                    await self._load_session(session_id)
                return session_id

            db_path = self._get_db_path(session_id)
            db_url = f"sqlite+aiosqlite:///{db_path}"

            try:
                engine = create_async_engine(db_url, echo=False)

                # Create all tables
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

                session_maker = async_sessionmaker(
                    engine, class_=AsyncSession, expire_on_commit=False
                )

                self._engines[session_id] = engine
                self._session_makers[session_id] = session_maker
                self._session_info[session_id] = {
                    "created_at": datetime.utcnow().isoformat(),
                    "db_path": db_path,
                }

                logger.info(f"Session '{session_id}' created: {db_path}")
                return session_id

            except Exception as e:
                # Cleanup on failure
                if os.path.exists(db_path):
                    os.remove(db_path)
                self._engines.pop(session_id, None)
                self._session_makers.pop(session_id, None)
                self._session_info.pop(session_id, None)
                raise RuntimeError(
                    f"Failed to create session '{session_id}': {e}"
                ) from e

    async def get_session(self, session_id: str) -> AsyncSession:
        """
        Get an async DB session for a specific session ID.

        Auto-creates the session if it doesn't exist (lazy creation).

        Args:
            session_id: The session identifier.

        Returns:
            An AsyncSession bound to the session's isolated database.
        """
        if session_id not in self._session_makers:
            if self.session_exists(session_id):
                await self._load_session(session_id)
            else:
                await self.create_session(session_id)

        return self._session_makers[session_id]()

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and remove its database file.

        Args:
            session_id: The session to delete.

        Returns:
            True if deleted, False if session didn't exist.
        """
        async with self._lock:
            # Dispose engine
            engine = self._engines.pop(session_id, None)
            if engine:
                await engine.dispose()

            self._session_makers.pop(session_id, None)
            self._session_info.pop(session_id, None)

            # Remove DB file
            db_path = self._get_db_path(session_id)
            if os.path.exists(db_path):
                os.remove(db_path)
                logger.info(f"Session '{session_id}' deleted: {db_path}")
                return True

            return False

    async def list_sessions(self) -> List[dict]:
        """List all known sessions (from memory + disk)."""
        sessions = []

        # Check disk for any sessions not in memory
        if os.path.exists(self.sessions_dir):
            for filename in os.listdir(self.sessions_dir):
                if filename.endswith(".db"):
                    sid = filename[:-3]  # strip .db
                    db_path = self._get_db_path(sid)
                    info = self._session_info.get(sid, {})
                    sessions.append({
                        "session_id": sid,
                        "created_at": info.get("created_at"),
                        "db_path": db_path,
                        "file_size": os.path.getsize(db_path),
                    })

        return sessions

    async def cleanup_all(self) -> int:
        """Delete ALL sessions. Used during shutdown or testing."""
        sessions = await self.list_sessions()
        count = 0
        for s in sessions:
            if await self.delete_session(s["session_id"]):
                count += 1
        return count

    async def _load_session(self, session_id: str):
        """Load an existing session from disk into memory."""
        db_path = self._get_db_path(session_id)
        if not os.path.exists(db_path):
            raise RuntimeError(f"Session DB not found: {db_path}")

        db_url = f"sqlite+aiosqlite:///{db_path}"
        engine = create_async_engine(db_url, echo=False)
        session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        self._engines[session_id] = engine
        self._session_makers[session_id] = session_maker
        self._session_info[session_id] = {
            "created_at": datetime.utcfromtimestamp(
                os.path.getctime(db_path)
            ).isoformat(),
            "db_path": db_path,
        }


# ── Global singleton ──
session_manager = SessionDatabaseManager()
