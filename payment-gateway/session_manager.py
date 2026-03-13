"""
Session Database Manager for the Payment Gateway gym.

Creates and manages isolated SQLite databases for concurrent evaluation sessions.
Each session gets its own DB file in data/sessions/, ensuring multiple agents
never interfere with each other's payment/refund/webhook state.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database import Base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "data", "sessions")

# Ensure models are registered with Base.metadata
import models  # noqa: F401

logger = logging.getLogger(__name__)


class SessionDatabaseManager:
    """
    Manages isolated SQLite databases per evaluation session.

    Each session creates a fresh DB with the full payment gateway schema.
    When deleted, the DB file is removed from disk.
    """

    def __init__(self, sessions_dir: str = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        self._engines: Dict[str, any] = {}
        self._session_makers: Dict[str, async_sessionmaker] = {}
        self._session_info: Dict[str, dict] = {}
        self._lock = asyncio.Lock()
        os.makedirs(self.sessions_dir, exist_ok=True)

    def _get_db_path(self, session_id: str) -> str:
        return os.path.join(self.sessions_dir, f"{session_id}.db")

    def session_exists(self, session_id: str) -> bool:
        return (
            session_id in self._engines
            or os.path.exists(self._get_db_path(session_id))
        )

    async def create_session(self, session_id: str) -> str:
        """Create a new session with an isolated SQLite database."""
        async with self._lock:
            if self.session_exists(session_id):
                if session_id not in self._engines:
                    await self._load_session(session_id)
                return session_id

            db_path = self._get_db_path(session_id)
            db_url = f"sqlite+aiosqlite:///{db_path}"

            try:
                eng = create_async_engine(db_url, echo=False)
                async with eng.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

                sm = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
                self._engines[session_id] = eng
                self._session_makers[session_id] = sm
                self._session_info[session_id] = {
                    "created_at": datetime.utcnow().isoformat(),
                    "db_path": db_path,
                }
                logger.info(f"Session '{session_id}' created: {db_path}")
                return session_id

            except Exception as e:
                if os.path.exists(db_path):
                    os.remove(db_path)
                self._engines.pop(session_id, None)
                self._session_makers.pop(session_id, None)
                self._session_info.pop(session_id, None)
                raise RuntimeError(f"Failed to create session '{session_id}': {e}") from e

    async def get_session(self, session_id: str) -> AsyncSession:
        """Get an async DB session for a given session ID (lazy-creates if needed)."""
        if session_id not in self._session_makers:
            if self.session_exists(session_id):
                await self._load_session(session_id)
            else:
                await self.create_session(session_id)
        return self._session_makers[session_id]()

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and remove its database file."""
        async with self._lock:
            eng = self._engines.pop(session_id, None)
            if eng:
                await eng.dispose()

            self._session_makers.pop(session_id, None)
            self._session_info.pop(session_id, None)

            db_path = self._get_db_path(session_id)
            if os.path.exists(db_path):
                os.remove(db_path)
                logger.info(f"Session '{session_id}' deleted: {db_path}")
                return True
            return False

    async def list_sessions(self) -> List[dict]:
        """List all known sessions."""
        sessions = []
        if os.path.exists(self.sessions_dir):
            for filename in os.listdir(self.sessions_dir):
                if filename.endswith(".db"):
                    sid = filename[:-3]
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
        """Delete ALL sessions. Used during shutdown."""
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
        eng = create_async_engine(db_url, echo=False)
        sm = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

        self._engines[session_id] = eng
        self._session_makers[session_id] = sm
        self._session_info[session_id] = {
            "created_at": datetime.utcfromtimestamp(os.path.getctime(db_path)).isoformat(),
            "db_path": db_path,
        }


# Global singleton
session_manager = SessionDatabaseManager()
