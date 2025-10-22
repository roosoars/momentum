import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...domain.models import Strategy, StrategySignal, User
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

                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    channel_identifier TEXT NOT NULL,
                    channel_id TEXT,
                    channel_title TEXT,
                    channel_linked_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    is_paused INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_strategies_channel_id
                    ON strategies(channel_id);

                CREATE TABLE IF NOT EXISTS strategy_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER NOT NULL,
                    channel_id TEXT NOT NULL,
                    telegram_message_id INTEGER NOT NULL,
                    raw_message TEXT,
                    parsed_payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    received_at TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    UNIQUE(strategy_id, telegram_message_id),
                    FOREIGN KEY(strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_strategy_signals_strategy_processed
                    ON strategy_signals(strategy_id, processed_at DESC);

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
        self._apply_migrations()

    def _apply_migrations(self) -> None:
        with self._lock:
            cur = self._conn.execute("PRAGMA table_info(strategies)")
            columns = {row[1] for row in cur.fetchall()}
        if "channel_linked_at" not in columns:
            with self._lock, self._conn:
                self._conn.execute("ALTER TABLE strategies ADD COLUMN channel_linked_at TEXT")

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

    # StrategyRepository API ------------------------------------------------
    def create_strategy(
        self,
        name: str,
        channel_identifier: str,
        channel_id: Optional[str],
        channel_title: Optional[str],
        channel_linked_at: Optional[str],
        is_active: bool,
    ) -> Strategy:
        now = self._now()
        linked_at = channel_linked_at or (now if channel_id else None)
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO strategies (
                    name, channel_identifier, channel_id, channel_title,
                    channel_linked_at, is_active, is_paused, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    name,
                    channel_identifier,
                    channel_id,
                    channel_title,
                    linked_at,
                    int(is_active),
                    now,
                    now,
                ),
            )
            strategy_id = cur.lastrowid
            cur = self._conn.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
            row = cur.fetchone()
        if not row:
            raise RuntimeError("Failed to persist strategy.")
        return self._row_to_strategy(row)

    def update_strategy(
        self,
        strategy_id: int,
        *,
        name: Optional[str] = None,
        channel_identifier: Optional[str] = None,
        channel_id: Optional[str] = None,
        channel_title: Optional[str] = None,
        channel_linked_at: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_paused: Optional[bool] = None,
    ) -> Strategy:
        updates = []
        params: List[Any] = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if channel_identifier is not None:
            updates.append("channel_identifier = ?")
            params.append(channel_identifier)
        if channel_id is not None:
            updates.append("channel_id = ?")
            params.append(channel_id)
        if channel_title is not None:
            updates.append("channel_title = ?")
            params.append(channel_title)
        if channel_linked_at is not None:
            updates.append("channel_linked_at = ?")
            params.append(channel_linked_at)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(int(is_active))
        if is_paused is not None:
            updates.append("is_paused = ?")
            params.append(int(is_paused))

        if updates:
            updates.append("updated_at = ?")
            params.append(self._now())
            params.append(strategy_id)
            statement = f"UPDATE strategies SET {', '.join(updates)} WHERE id = ?"
            with self._lock, self._conn:
                self._conn.execute(statement, params)
        with self._lock:
            cur = self._conn.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
            row = cur.fetchone()
        if not row:
            raise ValueError(f"Estratégia {strategy_id} não encontrada.")
        return self._row_to_strategy(row)

    def delete_strategy(self, strategy_id: int) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))

    def get_strategy(self, strategy_id: int) -> Optional[Strategy]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
            row = cur.fetchone()
        return self._row_to_strategy(row) if row else None

    def get_strategies(self) -> List[Strategy]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM strategies ORDER BY created_at ASC")
            rows = cur.fetchall()
        return [self._row_to_strategy(row) for row in rows]

    def get_strategies_by_channel(self, channel_id: str) -> List[Strategy]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM strategies WHERE channel_id = ?",
                (channel_id,),
            )
            rows = cur.fetchall()
        return [self._row_to_strategy(row) for row in rows]

    # StrategySignalRepository API -----------------------------------------
    def record_signal(
        self,
        strategy_id: int,
        channel_id: str,
        telegram_message_id: int,
        raw_message: Optional[str],
        parsed_payload: Dict[str, Any],
        status: str,
        error: Optional[str],
        received_at: str,
        processed_at: str,
    ) -> StrategySignal:
        payload_data = json.dumps(parsed_payload, ensure_ascii=False)
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO strategy_signals (
                    strategy_id, channel_id, telegram_message_id, raw_message,
                    parsed_payload, status, error, received_at, processed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(strategy_id, telegram_message_id)
                DO UPDATE SET
                    raw_message = excluded.raw_message,
                    parsed_payload = excluded.parsed_payload,
                    status = excluded.status,
                    error = excluded.error,
                    processed_at = excluded.processed_at
                """,
                (
                    strategy_id,
                    channel_id,
                    telegram_message_id,
                    raw_message,
                    payload_data,
                    status,
                    error,
                    received_at,
                    processed_at,
                ),
            )
            signal_id = cur.lastrowid
            if signal_id == 0:
                # When an UPDATE happens, SQLite reports lastrowid as 0, so fetch id manually.
                cur = self._conn.execute(
                    """
                    SELECT id FROM strategy_signals
                    WHERE strategy_id = ? AND telegram_message_id = ?
                    """,
                    (strategy_id, telegram_message_id),
                )
                row_id_row = cur.fetchone()
                signal_id = row_id_row["id"] if row_id_row else 0
            cur = self._conn.execute("SELECT * FROM strategy_signals WHERE id = ?", (signal_id,))
            row = cur.fetchone()
        if not row:
            raise RuntimeError("Failed to record strategy signal.")
        return self._row_to_signal(row)

    def get_signals_for_strategy(
        self,
        strategy_id: int,
        limit: int,
        newer_than: Optional[str] = None,
    ) -> List[StrategySignal]:
        query = """
            SELECT * FROM strategy_signals
            WHERE strategy_id = ?
        """
        params: List[Any] = [strategy_id]
        if newer_than:
            query += " AND processed_at >= ?"
            params.append(newer_than)
        query += " ORDER BY processed_at DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            cur = self._conn.execute(query, params)
            rows = cur.fetchall()
        return [self._row_to_signal(row) for row in rows]

    def purge_signals_older_than(self, iso_timestamp: str) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "DELETE FROM strategy_signals WHERE processed_at < ?", (iso_timestamp,)
            )
            return cur.rowcount

    # UserRepository API ----------------------------------------------------
    def get_user_by_email(self, email: str) -> Optional[User]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
            row = cur.fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
        return self._row_to_user(row) if row else None

    def create_user(self, email: str, password_hash: str) -> User:
        normalized = email.lower()
        now = self._now()
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO users (email, password_hash, is_active, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?)
                """,
                (normalized, password_hash, now, now),
            )
            user_id = cur.lastrowid
            cur = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
        if not row:
            raise RuntimeError("Failed to persist user.")
        return self._row_to_user(row)

    def update_user_password(self, user_id: int, password_hash: str) -> User:
        now = self._now()
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (password_hash, now, user_id),
            )
            cur = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
        if not row:
            raise ValueError(f"Usuário {user_id} não encontrado.")
        return self._row_to_user(row)

    # Helpers ----------------------------------------------------------------
    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        try:
            result = datetime.fromisoformat(value)
        except ValueError:
            # Fallback for legacy formats without 'T'
            result = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        if result.tzinfo is None:
            return result.replace(tzinfo=timezone.utc)
        return result.astimezone(timezone.utc)

    def _row_to_strategy(self, row: sqlite3.Row) -> Strategy:
        return Strategy(
            id=row["id"],
            name=row["name"],
            channel_identifier=row["channel_identifier"],
            channel_id=row["channel_id"],
            channel_title=row["channel_title"],
            channel_linked_at=self._parse_datetime(row["channel_linked_at"])
            if row["channel_linked_at"]
            else None,
            is_active=bool(row["is_active"]),
            is_paused=bool(row["is_paused"]),
            created_at=self._parse_datetime(row["created_at"]),
            updated_at=self._parse_datetime(row["updated_at"]),
        )

    def _row_to_signal(self, row: sqlite3.Row) -> StrategySignal:
        payload = json.loads(row["parsed_payload"])
        return StrategySignal(
            id=row["id"],
            strategy_id=row["strategy_id"],
            channel_id=row["channel_id"],
            telegram_message_id=row["telegram_message_id"],
            raw_message=row["raw_message"],
            parsed_payload=payload,
            status=row["status"],
            error=row["error"],
            received_at=self._parse_datetime(row["received_at"]),
            processed_at=self._parse_datetime(row["processed_at"]),
        )

    def _row_to_user(self, row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            is_active=bool(row["is_active"]),
            created_at=self._parse_datetime(row["created_at"]),
            updated_at=self._parse_datetime(row["updated_at"]),
        )
