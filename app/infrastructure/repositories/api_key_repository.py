"""Repository for ApiKey persistence."""

import sqlite3
from datetime import datetime
from typing import List, Optional

from app.domain.models.api_key import ApiKey


class ApiKeyRepository:
    """Repository for managing ApiKey entities in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialize_table()

    def _initialize_table(self) -> None:
        """Create api_keys table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    last_used_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key)"
            )
            conn.commit()

    def create(
        self,
        user_id: int,
        key: str,
        name: str,
    ) -> ApiKey:
        """Create a new API key."""
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO api_keys (
                    user_id, key, name, is_active, created_at, updated_at
                )
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (user_id, key, name, now, now),
            )
            conn.commit()
            api_key_id = cursor.lastrowid

        return ApiKey(
            id=api_key_id,
            user_id=user_id,
            key=key,
            name=name,
            is_active=True,
            last_used_at=None,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    def get_by_id(self, api_key_id: int) -> Optional[ApiKey]:
        """Get API key by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM api_keys WHERE id = ?", (api_key_id,)
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_api_key(row)

    def get_by_key(self, key: str) -> Optional[ApiKey]:
        """Get API key by key value."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM api_keys WHERE key = ? AND is_active = 1", (key,)
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_api_key(row)

    def list_by_user_id(self, user_id: int) -> List[ApiKey]:
        """List all API keys for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM api_keys
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()

        return [self._row_to_api_key(row) for row in rows]

    def update_last_used(self, api_key_id: int) -> None:
        """Update last used timestamp."""
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE api_keys
                SET last_used_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, api_key_id),
            )
            conn.commit()

    def deactivate(self, api_key_id: int) -> None:
        """Deactivate an API key."""
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE api_keys
                SET is_active = 0, updated_at = ?
                WHERE id = ?
                """,
                (now, api_key_id),
            )
            conn.commit()

    def delete(self, api_key_id: int) -> None:
        """Delete an API key."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM api_keys WHERE id = ?", (api_key_id,))
            conn.commit()

    def _row_to_api_key(self, row: sqlite3.Row) -> ApiKey:
        """Convert database row to ApiKey entity."""
        last_used = None
        if row["last_used_at"]:
            last_used = datetime.fromisoformat(row["last_used_at"])

        return ApiKey(
            id=row["id"],
            user_id=row["user_id"],
            key=row["key"],
            name=row["name"],
            is_active=bool(row["is_active"]),
            last_used_at=last_used,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
