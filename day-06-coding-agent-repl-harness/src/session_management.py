"""SQLite-based session persistence with LangGraph checkpointer."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.sqlite import SqliteSaver

DB_DIR = Path.home() / ".coding-agent-harness"
DB_PATH = DB_DIR / "sessions.db"


def init_db() -> sqlite3.Connection:
    """Initialize the SQLite database and create tables if needed.

    :return: SQLite connection
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata TEXT
        )
        """
    )
    conn.commit()
    return conn


def create_checkpointer(conn: sqlite3.Connection) -> SqliteSaver:
    """Create a LangGraph SqliteSaver from a connection.

    :param conn: SQLite connection
    :return: SqliteSaver instance
    """
    return SqliteSaver(conn)


def create_session(conn: sqlite3.Connection, thread_id: Optional[str] = None) -> str:
    """Create a new session record and return its thread_id.

    :param conn: SQLite connection
    :param thread_id: Optional thread ID (auto-generated if None)
    :return: thread_id
    """
    tid = thread_id or f"session-{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO sessions (session_id, thread_id, created_at, updated_at, metadata) "
        "VALUES (?, ?, ?, ?, ?)",
        (tid, tid, now, now, "{}"),
    )
    conn.commit()
    return tid


def update_session(conn: sqlite3.Connection, thread_id: str):
    """Update the session's updated_at timestamp.

    :param conn: SQLite connection
    :param thread_id: Thread ID
    """
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE sessions SET updated_at = ? WHERE thread_id = ?", (now, thread_id)
    )
    conn.commit()


def list_sessions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """List all sessions ordered by most recently updated.

    :param conn: SQLite connection
    :return: List of session dicts
    """
    rows = conn.execute(
        "SELECT session_id, thread_id, created_at, updated_at, metadata "
        "FROM sessions ORDER BY updated_at DESC"
    ).fetchall()
    return [
        {
            "session_id": r[0],
            "thread_id": r[1],
            "created_at": r[2],
            "updated_at": r[3],
            "metadata": r[4],
        }
        for r in rows
    ]


