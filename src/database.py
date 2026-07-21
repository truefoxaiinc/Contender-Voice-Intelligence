import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from src.config import DATA_DIR

DB_PATH = Path(DATA_DIR) / "contender.db"


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS calls (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL,
                transcript TEXT NOT NULL DEFAULT '',
                caller_name TEXT,
                caller_phone TEXT,
                company_name TEXT,
                category TEXT NOT NULL DEFAULT 'General Inquiry',
                priority TEXT NOT NULL DEFAULT 'Normal',
                priority_reason TEXT NOT NULL DEFAULT 'Not analyzed yet.',
                summary TEXT NOT NULL DEFAULT 'Awaiting analysis.',
                important_information TEXT NOT NULL DEFAULT '[]',
                recommended_next_action TEXT NOT NULL DEFAULT 'Analyze this call.',
                missing_information TEXT NOT NULL DEFAULT '[]',
                confidence_notes TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'New',
                processing_status TEXT NOT NULL DEFAULT 'Uploaded',
                processing_error TEXT,
                transcript_segments TEXT NOT NULL DEFAULT '[]',
                created_by INTEGER
            );
            CREATE TABLE IF NOT EXISTS call_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                previous_value TEXT,
                new_value TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(call_id) REFERENCES calls(id)
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
        existing = {row[1] for row in db.execute("PRAGMA table_info(calls)")}
        if "processing_error" not in existing:
            db.execute("ALTER TABLE calls ADD COLUMN processing_error TEXT")
        if "transcript_segments" not in existing:
            db.execute("ALTER TABLE calls ADD COLUMN transcript_segments TEXT NOT NULL DEFAULT '[]'")
        if "created_by" not in existing:
            db.execute("ALTER TABLE calls ADD COLUMN created_by INTEGER")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


JSON_FIELDS = {"important_information", "missing_information", "confidence_notes", "transcript_segments"}


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for field in JSON_FIELDS:
        item[field] = json.loads(item.get(field) or "[]")
    return item


def get_call(call_id: str) -> dict[str, Any] | None:
    with connection() as db:
        row = db.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
    return row_to_dict(row) if row else None


def add_event(call_id: str, event_type: str, previous: str | None, new: str | None) -> None:
    with connection() as db:
        db.execute(
            "INSERT INTO call_events(call_id,event_type,previous_value,new_value,timestamp) VALUES(?,?,?,?,?)",
            (call_id, event_type, previous, new, now_iso()),
        )


def get_events(call_id: str) -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM call_events WHERE call_id = ? ORDER BY timestamp DESC, id DESC",
            (call_id,),
        ).fetchall()
    return [dict(row) for row in rows]
