import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...domain.ports.persistence import PersistenceGateway


class SQLitePersistence(PersistenceGateway):
    """SQLite-backed implementation of the persistence gateway."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._initialize()

    def _initialize(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    channel_id TEXT NOT NULL,
                    sender TEXT,
                    message TEXT,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(telegram_id, channel_id)
                );
                """
            )

    def close(self) -> None:
        self._conn.close()

    # SettingsRepository API -------------------------------------------------
    def get_setting(self, key: str) -> Optional[str]:
        with self._lock:
            cur = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    # MessageRepository API --------------------------------------------------
    def save_message(
        self,
        telegram_id: int,
        channel_id: str,
        sender: Optional[str],
        message: Optional[str],
        payload: Dict[str, Any],
        created_at: str,
    ) -> None:
        data = json.dumps(payload, default=str, ensure_ascii=False)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO messages (
                    telegram_id, channel_id, sender, message, payload, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (telegram_id, channel_id, sender, message, data, created_at),
            )

    def clear_messages_for_channel(self, channel_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))

    def get_recent_messages(self, channel_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
        query = "SELECT telegram_id, channel_id, sender, message, payload, created_at FROM messages"
        params: List[Any] = []
        if channel_id:
            query += " WHERE channel_id = ?"
            params.append(channel_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            cur = self._conn.execute(query, params)
            rows = cur.fetchall()
        return [
            {
                "telegram_id": row["telegram_id"],
                "channel_id": row["channel_id"],
                "sender": row["sender"],
                "message": row["message"],
                "payload": json.loads(row["payload"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
